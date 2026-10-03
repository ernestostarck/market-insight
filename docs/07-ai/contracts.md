# Contratos de ejecución NLP

## Flujo y límites de ejecución

```text
API -> Preprocessing -> Rule preview (síncrono, advisory, no persistido — POST /classify)

API -> Preprocessing -> Redis queue -> NLP Worker
    -> Classification (diccionario + reglas + modelo) -> Embeddings -> Knowledge (PostgreSQL + pgvector) -> Review
```

`preprocessing` es síncrono, determinístico y libre de I/O — igual que el rule
preview de `POST /classify`, que ejecuta `RuleEngine` en memoria pero nunca
pasa por `NLPJobRequest` ni persiste nada. `classification`, `embeddings` y
`knowledge` son los stages asíncronos: el worker los ejecuta fuera de la
solicitud HTTP. Esta asignación está representada y probada por
`PipelineStage` y `processing_mode`. El rule preview y el stage `classification`
no son la misma cosa vista dos veces — ver
[ADR 0002](../decisions/0002-nlp-sync-rule-preview-vs-async-classification.md)
para el porqué.

## Componentes

| Componente | Contrato | Responsabilidad |
| --- | --- | --- |
| API / `NLPService` | Entrada HTTP validada | Preprocesa, aplica reglas y encola la parte pesada. |
| Redis | `NLPJobRequest` | Entrega un trabajo idempotente al worker. |
| `NLP Worker` | `NLPJobRequest` | Genera vectores, predice, calcula confianza y solicita persistencia. |
| PostgreSQL + pgvector | resultados y artefactos versionados | Auditoría, consulta semántica y revisión humana. |

## Versionado reproducible

Cada `NLPJobRequest` lleva `ArtifactVersions`: taxonomía, dataset, modelo, modelo de embeddings y conjunto de reglas. Todos se versionan de forma inmutable y semántica, por ejemplo `taxonomy-2026.1`, `gold-2026.1` y `classifier-1.0`. Ver [`taxonomy.md`](taxonomy.md), [`semantic-dictionary.md`](semantic-dictionary.md) y [`model-versioning.md`](model-versioning.md) para la estrategia de cada artefacto.

La clave de idempotencia reúne el ID de licitación, hash del texto y cada versión. Por ello, reintentar el mismo trabajo no crea una ejecución duplicada; cambiar cualquier artefacto produce una ejecución nueva y trazable. Promover o revertir un modelo, taxonomía o dataset consiste en seleccionar otra versión registrada, nunca mutar una predicción histórica.

## Resultado del job

El worker devuelve un `JobResult` (`app/nlp/contracts.py`) al terminar de
ejecutar los stages asíncronos vía `execute_nlp_job`/`StageRegistry`
(`app/nlp/stages.py`): qué stages se completaron, cuáles quedan pendientes, un
`JobStatus` (`queued` | `partial` | `succeeded` | `failed`) y, si algo falló,
un `JobError` con el stage y el motivo. `StageRegistry.run` se detiene en el
primer stage que falla — los stages posteriores no se ejecutan y quedan como
`pending`, no como `failed`, porque `classification -> embeddings -> knowledge`
son secuencialmente dependientes. `JobStatus` no reutiliza los estados
internos de Celery (PENDING/STARTED/RETRY): esos describen mecánica de cola,
no avance del pipeline de stages.

Hoy `JobResult` se retorna del task de Celery pero no se expone todavía por un
endpoint HTTP de estado — eso depende de si 6.6 persiste el estado en la base
de datos o se consulta desde el result backend de Celery.

## Nota sobre el nombre `Rule`

`app.nlp.rules.Rule` (dataclass en memoria, evaluado por `RuleEngine`) y
`app.models.knowledge.Rule` (fila persistida en `knowledge.rules`, 6.7) son el
mismo concepto en dos etapas de su ciclo de vida, no un choque de nombres
accidental. Se recomienda importar con alias cuando ambos coexisten en un
mismo módulo (`from app.models.knowledge import Rule as RuleModel`) en vez de
renombrar cualquiera de los dos.
