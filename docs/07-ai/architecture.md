# Arquitectura NLP

## Flujo

```text
Preprocessing -> NLP -> Classification -> Embeddings -> Knowledge
```

| Stage | Modo | Componente dueño | ¿Persiste en `knowledge`? |
| --- | --- | --- | --- |
| `preprocessing` | síncrono | `NLP Service` (`TextPreprocessor`) | No |
| `nlp` | síncrono | `NLP Service` | No |
| `classification` | asíncrono | `NLP Worker` (`StageRegistry`) | Sí — `knowledge.classifications` |
| `embeddings` | asíncrono | `NLP Worker` | Sí — `knowledge.embeddings` |
| `knowledge` | asíncrono | `NLP Worker` | Sí — persistencia final del job |

`Preprocessing` conserva y normaliza el texto. `NLP` identifica señales
lingüísticas, entidades y atributos. `Classification` combina las señales del
diccionario, las reglas y los modelos. `Embeddings` genera la representación
semántica. `Knowledge` persiste documentos, entidades, clasificaciones y
vectores en PostgreSQL con pgvector. La partición síncrono/asíncrono está
fijada por `PipelineStage`/`SYNC_STAGES`/`ASYNC_STAGES`/`processing_mode`
(`app/nlp/contracts.py`) y probada por
`tests/nlp/test_architecture.py::test_every_pipeline_stage_has_one_execution_mode`.

El documento consolidado que arranca el pipeline (`preprocessing`) se
construye en `app/nlp/document.py` — ver
[`document-processing.md`](document-processing.md) para la estructura
`Document`/`Chunk` y qué fuentes textuales están activas hoy. La limpieza y
normalización de texto en sí (`TextPreprocessor`) está documentada en
[`text-preprocessing.md`](text-preprocessing.md).

## NLP Service

Parte de FastAPI (`app/services/nlp.py`, expuesto en
`app/api/v1/endpoints/nlp.py`). Responsabilidades:

- Validar la solicitud HTTP (vía los schemas Pydantic de `app/schemas/nlp.py`).
- Ejecutar `preprocessing` de forma síncrona (`TextPreprocessor`).
- Ejecutar el rule preview síncrono, advisory (`RuleEngine.evaluate` vía
  `classify_by_rules` — ver "Límite síncrono/asíncrono" abajo).
- Construir un `NLPJobRequest` con `ArtifactVersions` y despacharlo al worker
  (`NLPJobDispatcher`, hoy `CeleryNLPJobDispatcher`).

Lo que el NLP Service **no** hace: no ejecuta inferencia de modelos, no genera
embeddings, no escribe en `knowledge.*`, no reintenta trabajo fallido. Todo
eso vive en el NLP Worker — mantener esta línea es lo que permite que la API
responda rápido sin bloquear en trabajo caro.

## NLP Worker

`app/worker/nlp_tasks.py` es el punto de entrada Celery
(`process_nlp_job`, cola `nlp`, `acks_late=True`), pero deliberadamente es un
*composition root* delgado: resuelve el payload en un `NLPJobRequest` y delega
toda la orquestación a `execute_nlp_job` (`app/nlp/stages.py`), que es pura y
testeable sin Celery.

La extensión para subfases futuras (6.6 Knowledge Layer en adelante) es
`StageRegistry`: un registro `PipelineStage -> StageExecutor` que
`execute_nlp_job` recorre en orden, deteniéndose en el primer stage que falla
(`classification -> embeddings -> knowledge` son secuencialmente dependientes,
así que un fallo en `classification` no debe dejar correr `embeddings` sobre
un resultado incompleto). Cada subfase agrega **una línea** a
`STAGE_REGISTRY` en `app/worker/nlp_tasks.py` — no vuelve a tocar el task de
Celery. Hoy `STAGE_REGISTRY` está vacío: el worker acepta el job, no ejecuta
ningún stage real todavía, y devuelve `JobStatus.PARTIAL` con los tres stages
asíncronos en `pending_stages`.

## Límite síncrono/asíncrono

`PipelineStage` modela exclusivamente el pipeline asíncrono persistido. El
rule preview síncrono expuesto en `POST /classify` (match de reglas en
memoria contra `RuleEngine`, sin persistir, sin construir un `NLPJobRequest`)
**no** es un `PipelineStage` — es una capacidad de API aparte. Ver
[ADR 0002](../decisions/0002-nlp-sync-rule-preview-vs-async-classification.md)
para las alternativas consideradas y por qué no se agregó un stage `RULES` ni
se hizo `CLASSIFICATION` condicionalmente síncrono.

## Contratos

Los contratos compartidos están en `app.nlp.contracts`: cada job incluye el
identificador de la licitación, el hash del contenido y las versiones de
taxonomía, diccionario semántico, modelo y embeddings
(`NLPJobRequest`/`ArtifactVersions`). La clave de idempotencia reúne esos
valores. El worker devuelve un `JobResult`/`JobStatus`/`JobError` al terminar
— ver [`contracts.md`](contracts.md) para el detalle del contrato de
resultado.

## Versionado

Tres artefactos se versionan de forma inmutable; una predicción conserva
siempre las versiones con que fue generada, y promover o revertir un artefacto
selecciona otra versión sin modificar una ejecución histórica:

- **Modelos** — estados `draft` / `staging` / `production` / `archived` y su
  máquina de transición: [`model-versioning.md`](model-versioning.md).
- **Taxonomías** — versión append-only `taxonomy-<label>`:
  [`taxonomy.md`](taxonomy.md).
- **Diccionario semántico** — versión append-only `dictionary-<label>`,
  independiente de la taxonomía: [`semantic-dictionary.md`](semantic-dictionary.md).

## Referencias

- [ADR 0001 — Workers del ETL: Celery vs ARQ](../decisions/0001-workers-celery-vs-arq.md)
  (el NLP Worker reutiliza el mismo `celery_app`, no una decisión aparte).
- [ADR 0002 — Rule preview síncrono vs. stage Classification asíncrono](../decisions/0002-nlp-sync-rule-preview-vs-async-classification.md).
