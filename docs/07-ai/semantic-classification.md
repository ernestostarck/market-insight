# NLP Semantic Classification

Segundo stage real del pipeline asíncrono (`PipelineStage.EMBEDDINGS`,
`EmbeddingsStageExecutor` en `STAGE_REGISTRY`,
`app/worker/nlp_tasks.py`). Corre después de `CLASSIFICATION` (reglas) y
antes de `KNOWLEDGE` — combina su score con el de las reglas en la misma
fila de `knowledge.classifications`, no crea una clasificación paralela.

## Modelo elegido

`paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers), 384
dimensiones — calza exactamente con `Vector(384)` fijado en 6.6. Es
multilingüe con buen soporte de español, liviano dentro de la familia de
sentence-transformers (12 capas, ~470MB de pesos). Se aceptó explícitamente
agregar `torch`/`sentence-transformers` como dependencia nueva (decisión
tomada con el usuario durante la planificación de 6.8) en vez de una
alternativa liviana basada en TF-IDF — el nombre de la fase ("NLP Semantic
Classification") y el hecho de que 384 dims ya estaba fijado apuntaban a
embeddings semánticos reales, no léxicos.

`app/ml/embeddings.py::EmbeddingService` carga el modelo perezosamente (en
el primer `.encode()`, no al importar el módulo) — así los tests que
inyectan un modelo falso, o que no ejercitan el encoder, no pagan el costo
ni requieren red. `encode()` normaliza los vectores a norma unitaria
(`normalize_embeddings=True`), así la similitud coseno es directamente un
producto punto.

## `EmbeddingsStageExecutor` (`app/nlp/semantic.py`)

1. Busca `knowledge.documents` por `(licitacion_id, content_hash)` — igual
   que `ClassificationStageExecutor`. Sin documento, `return False`.
2. Embebe el texto normalizado, get-or-create `knowledge.model_versions`
   (`name`+`version` -> `status="production"`, no hay máquina de promoción
   todavía — es el único modelo, ver "Fuera de alcance" en el plan de
   6.7/6.8), inserta la fila en `knowledge.embeddings`.
3. **Embeddings de conceptos/categorías: en memoria, no persistidos.**
   Se calculan una sola vez por instancia del executor (`__init__`,
   nombre + descripción de cada uno de los ~15 nodos de la taxonomía),
   cacheados mientras el proceso worker vive. Decisión tomada con el
   usuario: son pocos, 100% derivables de `taxonomy.json` + el modelo, y
   agregar una tabla para cachearlos era complejidad sin beneficio claro
   en esta fase.
4. `semantic_score` = similitud coseno máxima entre el vector del
   documento y los vectores de concepto (`cosine_similarity`,
   `app/nlp/semantic.py`). Si supera `_SIMILARITY_THRESHOLD = 0.5`
   (constante documentada, inicial — igual que `_RULE_SCORE_SATURATION`
   en 6.7, el ajuste real es 6.23 MLOps & Evaluation), se resuelve la
   categoría/subcategoría del concepto ganador (mismos helpers
   get-or-create que 6.7, extraídos a `app/nlp/taxonomy_db.py`).
5. Busca la fila de `knowledge.classifications` más reciente para
   `(licitacion_id, taxonomy_version)` — la que dejó `CLASSIFICATION` — y
   la actualiza: `similarity_score = semantic_score`,
   `confidence_score = max(confidence_score_actual, semantic_score)`.
   Sin fila previa (defensivo, no debería pasar dado el orden del
   pipeline), crea una nueva con `rule_score=NULL`.

`Classification.model_score` queda `NULL` en esta fase — está reservado
para un clasificador entrenado que todavía no existe (fuera de alcance de
6.7/6.8).

## Por qué esto no es 6.9 (pgvector)

Esta fase solo compara el embedding del documento contra los ~15 nodos de
la taxonomía **en memoria** — no hay índice vectorial, no hay `top-k`, no
hay búsqueda de licitaciones similares entre sí. Eso es exactamente el
alcance de 6.9 (pgvector: índices ANN, `top-k`, filtros combinados) y 6.10
(Hybrid Search). `knowledge.embeddings` ya persiste el vector real de cada
licitación desde esta fase, listo para que 6.9 lo indexe.

## Validado con datos reales

Con el modelo real (no el fake de los tests unitarios) contra el Postgres
dev real, corriendo `CLASSIFICATION` y `EMBEDDINGS` en secuencia sobre dos
textos: uno claramente del dominio (sillas de ruedas, ayudas técnicas,
discapacidad, rampas, ELEAM) y uno claramente no (notebooks y licencias de
oficina):

| | `rule_score` | `similarity_score` | `confidence_score` | categoría resuelta |
| --- | --- | --- | --- | --- |
| Texto relevante | 1.0 | 0.76 | 0.76 (= similarity, gana sobre 0.33 de reglas) | `health/assistive-technology` |
| Texto no relevante | 0.0 | 0.25 (bajo el threshold 0.5) | 0.25 | `NULL` |

Y aislado, comparando solo embeddings: el texto relevante tiene similitud
0.64 contra el concepto "discapacidad"; el no relevante, 0.08 — separación
clara. Confirma que el modelo multilingüe discrimina bien el dominio en
español, que el threshold de 0.5 es razonable como punto de partida, y que
`confidence_score = max(rule, semantic)` combina ambas señales sin que una
opaque a la otra cuando solo una dispara.

## Ver también

- [`rule-classification.md`](rule-classification.md) — el otro score que se combina en la misma fila.
- [`taxonomy.md`](taxonomy.md) — los nodos que se embeben.
- [`architecture.md`](architecture.md) — orden del pipeline y por qué `EMBEDDINGS` va después de `CLASSIFICATION`.
