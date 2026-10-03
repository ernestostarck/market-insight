# Hybrid Search

Combina búsqueda de texto completo (PostgreSQL FTS) y búsqueda semántica
(6.9, `VectorSearchRepository`) sobre licitaciones. No agrega un endpoint
FastAPI nuevo — igual que 6.7-6.9, eso es 6.18/6.21.

`app/services/search.py` (`SearchService`) es un servicio distinto y
anterior — búsqueda federada por ILIKE sobre licitación/proveedor/
organismo, sin nada de NLP. No se tocó; 6.10 vive en
`app/services/hybrid_search.py`, específico a licitaciones vía las
capacidades NLP.

## Full-text search: `tsvector` generado + GIN, en español

`alembic/versions/20260828_0010_add_licitacion_fulltext_search.py` agrega
una columna `search_vector tsvector GENERATED ALWAYS AS (to_tsvector(
'spanish', coalesce(nombre,'') || ' ' || coalesce(descripcion,'')))
STORED` + índice GIN, tanto en `core.licitacion` (búsqueda general) como
en `core.licitacion_item` (búsqueda por productos — items ya poblados por
el enriquecimiento bajo demanda de 6.2). El diccionario `spanish` de
Postgres stemea automáticamente (verificado: buscar "silla" encuentra una
licitación cuyo texto solo dice "sillas").

## Por qué embeber la query del usuario SÍ es correcto acá

`docs/07-ai/architecture.md` prohíbe inferencia de modelos en el NLP
Service — por eso 6.8/6.9 precomputan los vectores de concepto/categoría
una sola vez (`app/nlp/taxonomy_vectors.py`) en vez de recalcularlos por
request. Esa regla es sobre **no correr inferencia sobre el contenido
masivo de licitaciones en el camino síncrono** — documentos completos,
muchos por segundo potencialmente.

Buscar semánticamente por texto libre de un usuario es un caso distinto:
no existe manera de precomputar el embedding de una query arbitraria, y
embeber unas pocas palabras es barato (no un documento completo). Es
exactamente lo que hace cualquier sistema de búsqueda híbrida.
`HybridSearchService.search()` (`app/services/hybrid_search.py`) sí llama
a `EmbeddingService.encode([query])` en el momento de la búsqueda — una
decisión consciente, distinta de (y no una violación de) la regla que
gobierna el pipeline de clasificación.

## Combinación: Reciprocal Rank Fusion (RRF)

`ts_rank` (no acotado, depende del corpus) y similitud coseno (acotada
0-1) no son comparables directamente sin una calibración arbitraria — eso
es trabajo de 6.23 (MLOps & Evaluation) con datos de evaluación reales,
no algo para inventar ahora. RRF evita el problema por completo: usa solo
la *posición* de cada documento en cada lista, no su score crudo —
`score(doc) = Σ 1 / (60 + rank_en_lista)` sobre las listas donde aparece.
Un documento que aparece en texto completo Y en semántica suma ambos
términos y sube naturalmente — esa es la señal "híbrida" real. `k=60` es
la constante estándar del paper original de RRF.

## `HybridSearchRepository` (`app/repositories/hybrid_search.py`)

- `search_fulltext(query)` — `plainto_tsquery('spanish', ...)` contra
  `core.licitacion.search_vector`, `ORDER BY ts_rank DESC`.
- `search_products(query)` — igual contra `core.licitacion_item`, agrupado
  por licitación (varios ítems pueden matchear la misma licitación).
- `search_by_code(code)` — exacto (`=`) primero, luego prefijo (`ILIKE`).
  Deliberadamente sin FTS: un código no es texto natural, stemear un
  código produciría resultados sin sentido.

## `HybridSearchService` (`app/services/hybrid_search.py`)

- `search(query)` — el híbrido de verdad: FTS + semántica, combinados por
  RRF. Secuencial, no `asyncio.gather` — ambos comparten la misma
  `AsyncSession`, y SQLAlchemy no permite dos operaciones concurrentes
  sobre una sesión (`InvalidRequestError`, confirmado contra Postgres
  real durante la validación de esta fase — bug real encontrado y
  corregido, no solo una precaución teórica). `HybridSearchResult.matched_via`
  indica si un resultado vino de texto, semántica, o ambos.
- `search_by_code`/`search_products` — passthrough al repositorio.
- `search_by_concept`/`search_by_category` — passthrough a
  `VectorSearchRepository` (6.9), reusando los vectores de concepto/
  categoría precomputados una sola vez en `__init__`.

## Validado

**Con Postgres real** (`tests/repositories/test_hybrid_search_integration.py`,
marcador `integration`): 4/4 — stemming español real ("silla" encuentra
"sillas"), sin falsos positivos con texto no relacionado, búsqueda por
producto vía `core.licitacion_item`, código exacto y prefijo.

**Con repositorios fake + RRF** (`tests/services/test_hybrid_search.py`):
5/5 — un documento en ambas listas rankea sobre uno en una sola,
`matched_via` correcto, `top_k` respetado, la query se embebe una vez por
búsqueda, y `search_by_concept`/`search_by_category` reusan los vectores
precomputados (no llaman a `encode()` de nuevo).

**Con el modelo real de embeddings, punta a punta contra Postgres real**
(3 licitaciones: una sobre sillas de ruedas, una paráfrasis sin
vocabulario compartido — "dispositivos de apoyo a la movilidad para
personas con capacidades diferentes" — y una no relacionada, oficina):

| Query | 1er lugar | 2do | 3ro |
| --- | --- | --- | --- |
| "sillas de ruedas" | sillas de ruedas (`fulltext`+`semantic`, score 0.033) | paráfrasis (`semantic`, 0.016) | oficina (`semantic`, 0.016) |
| "apoyo a la movilidad para discapacidad" | **paráfrasis** (`semantic`, 0.016) | sillas de ruedas (`semantic`, 0.016) | oficina (`semantic`, 0.016) |

Confirma las dos propiedades que importan: (1) RRF sube al documento que
matchea ambas señales muy por sobre los que matchean solo una (0.033 vs.
0.016), y (2) la búsqueda semántica encuentra correctamente la paráfrasis
sin vocabulario compartido y la rankea primero cuando la query se acerca
más a su significado — el objetivo central de "búsqueda híbrida". De paso,
esta corrida encontró y corrigió el bug real de `asyncio.gather` sobre una
sesión compartida (ver arriba).

## Fuera de alcance (explícito)

- Endpoint FastAPI — 6.18/6.21.
- Extracción de productos/atributos desde texto libre (NER) — 6.11/6.12;
  "búsqueda por productos" acá es sobre `core.licitacion_item`, ya
  estructurado, no sobre texto extraído.
- Cambios a `SearchService` (búsqueda federada no-NLP).

## Ver también

- [`pgvector.md`](pgvector.md) — `VectorSearchRepository`, de donde viene la mitad semántica.
- [`semantic-classification.md`](semantic-classification.md) — quién escribe `knowledge.embeddings`.
