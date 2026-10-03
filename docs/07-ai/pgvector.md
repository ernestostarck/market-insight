# pgvector

Búsqueda vectorial real sobre `knowledge.embeddings` (6.8 ya persiste ahí el
embedding de cada licitación; esta fase la hace buscable en Postgres). No
agrega un endpoint FastAPI nuevo — esa es explícitamente 6.18
(`SemanticSearchService`) y 6.21 (NLP API), igual que 6.7/6.8 no agregaron
uno propio.

## Índice: HNSW, no ivfflat

`knowledge.embeddings.vector` (`Vector(384)`, fijado en 6.6) gana un índice
`USING hnsw (vector vector_cosine_ops)`
(`alembic/versions/20260828_0009_add_embeddings_vector_index.py`). Se
eligió HNSW sobre ivfflat porque `knowledge.embeddings` tenía 0 filas reales
en producción al construir esta fase (6.7/6.8 recién persistieron el
esquema) — ivfflat necesita datos existentes para calibrar bien su
parámetro `lists`; HNSW se construye incrementalmente y es efectivo desde
la primera fila. pgvector 0.8.6 (verificado: `SELECT extversion FROM
pg_extension WHERE extname='vector'`).

## La restricción "sin inferencia en el request path"

`docs/07-ai/architecture.md` fija que el NLP Service (la parte síncrona,
FastAPI) "no ejecuta inferencia de modelos". Buscar por concepto o
categoría necesita el vector de ese concepto/categoría — pero no se
recalcula en cada búsqueda: `app/nlp/taxonomy_vectors.py` (nuevo,
extraído de `EmbeddingsStageExecutor._build_concept_nodes`, 6.8) expone
`build_concept_vectors`/`build_category_vectors`, pensadas para
construirse **una sola vez** por proceso (mismo patrón que `_RULE_ENGINE`
en `app/db/dependencies.py`) y reutilizarse — el costo de inferencia se
paga una vez al arrancar el proceso que las use, nunca por request.
`EmbeddingsStageExecutor` (worker) ya se refactorizó para usar este helper
compartido en vez de duplicar la lógica.

## `VectorSearchRepository` (`app/repositories/vector_search.py`)

Async, `AsyncSession` — mismo estilo que `AnalyticsRepository`
(`app/repositories/analytics.py`) — pero con SQL crudo vía `text()` para
el operador de distancia (`<=>`, `vector_cosine_ops`): no hay soporte de
expresión SQLAlchemy para la columna `Vector` custom, mismo motivo por el
que 6.6-6.8 ya usan `text()` ahí.

- **`search_by_vector`**: el método base — distancia coseno, `similarity =
  1 - distance` (los vectores de `EmbeddingService` ya vienen
  normalizados), `top_k` (`LIMIT`), `min_similarity` (threshold, filtra en
  el `WHERE`), `exclude_licitacion_id`, y `category_code` (el filtro
  combinado del checklist — `JOIN` contra la clasificación más reciente de
  cada licitación). Solo considera el embedding **más reciente** de cada
  licitación (`DISTINCT ON` + `ORDER BY created_at DESC`) — mezclar
  vectores de modelos distintos no tendría sentido, y hoy solo hay un
  modelo en juego así que "el más reciente" es la regla correcta.
- **`find_similar_to_licitacion`**: resuelve el embedding de una licitación
  y delega a `search_by_vector` excluyéndose a sí misma.
- **`search_by_concept`/`search_by_category`**: reciben el vector ya
  calculado (`ConceptVector`/`CategoryVector` de `taxonomy_vectors.py`) —
  no llaman a `EmbeddingService` ellos mismos, por la restricción de
  arriba.

## Validado

**Con Postgres real** (`tests/repositories/test_vector_search_integration.py`,
marcador `integration`, excluido por defecto —
`pytest -m integration -v`): 4 tests contra el índice HNSW real con
vectores de control (ejes conocidos) — ranking por similitud coseno
descendente correcto (1.0, 0.8, 0.0), threshold, `top_k`, exclusión de la
propia licitación en `find_similar_to_licitacion`. Todos limpian sus
propias filas al terminar.

**Con el modelo real de embeddings** (`search_by_concept`/
`search_by_category` con datos reales, la validación semántica de punta a
punta): bloqueada por la misma directiva de Control de aplicaciones de
Windows que interrumpió la verificación de 6.7/6.8 — esta vez sobre una
DLL de `scipy` que trae `sentence-transformers` de forma transitiva, en el
venv recreado. No es un problema del código: el modelo ya se validó
extensamente con datos reales en 6.8 (`docs/07-ai/semantic-classification.md`,
separación 0.76 vs. 0.25), y la parte que le tocaba probar a esta fase — la
consulta SQL/índice — está probada de verdad contra Postgres. Queda
pendiente re-correr `verify_pgvector_real.py` (script de un solo uso, no
versionado) cuando el bloqueo se despeje, para la confirmación semántica
combinada.

## Fuera de alcance (explícito)

- Endpoint FastAPI — 6.18/6.21.
- Full-text search / combinación híbrida — 6.10.
- Cache persistente de vectores de concepto/categoría en Postgres —
  descartado también en 6.8 (decisión del usuario), misma postura aquí.

## Ver también

- [`semantic-classification.md`](semantic-classification.md) — quién escribe `knowledge.embeddings`.
- [`knowledge-layer.md`](knowledge-layer.md) — esquema de `knowledge.embeddings`.
