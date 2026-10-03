# ADR 0002 — NLP: rule preview síncrono vs. stage `Classification` asíncrono

- **Fecha**: 2026-08-20
- **Fase**: 6.1 — Arquitectura NLP
- **Estado**: Aceptado

## Contexto

`PipelineStage` (`app/nlp/contracts.py`) modela el pipeline asíncrono persistido:
`preprocessing`, `nlp`, `classification`, `embeddings`, `knowledge`. `CLASSIFICATION`
está en `ASYNC_STAGES` — combina diccionario, reglas y modelo, y persiste en
`knowledge.classifications`.

Al mismo tiempo, `POST /classify` (`app/api/v1/endpoints/nlp.py`,
`NLPService.classify_by_rules`) ejecuta un match de reglas en memoria contra
`RuleEngine`, de forma síncrona, sin persistir nada y sin construir un
`NLPJobRequest`. La documentación previa (`docs/07-ai/contracts.md`) llamaba a
esto simplemente "rules" como si fuera un paso más del flujo, lo que sugería
que "Rules" y "Classification" eran la misma etapa vista dos veces — no lo son:
una es una vista previa advisory sin estado, la otra es la etapa persistida y
versionada que produce el resultado real de clasificación.

Había que decidir cómo representar esta dualidad sin romper la invariante ya
fijada por `tests/nlp/test_architecture.py::test_every_pipeline_stage_has_one_execution_mode`
(cada `PipelineStage` tiene exactamente un modo de ejecución, función pura del
propio stage).

## Opciones consideradas

### A. Agregar `PipelineStage.RULES` como stage síncrono

- **Ventajas**: el flujo documentado ("Rules" antes de la cola) tendría un
  miembro de enum correspondiente.
- **Desventajas**:
  - Forzaría cambiar la forma de `NLPJobRequest`/`idempotency_key` para algo
    que nunca se persiste ni se encola — el idempotency key existe
    específicamente para deduplicar trabajo asíncrono, y un paso síncrono no
    lo necesita.
  - Duplicaría el mismo `RuleEngine` que el stage async `CLASSIFICATION` usará
    una vez las reglas estén en base de datos (6.7): dos "stages" ejecutando
    la misma lógica no aporta valor de enforcement, solo confusión de nombres.

### B. Hacer `CLASSIFICATION` condicionalmente síncrono cuando solo hay match de reglas

- **Ventajas**: evitaría introducir un concepto nuevo.
- **Desventajas**:
  - `processing_mode(stage)` es una función pura de `PipelineStage` — hacerla
    depender del contenido en tiempo de ejecución rompe esa invariante y el
    test que la fija.
  - Complica idempotencia y métricas de cola: el mismo stage tendría dos
    caminos de ejecución con garantías distintas, sin beneficio medible (un
    match de reglas puro sigue siendo barato de ejecutar async).

### C. Mantener `PipelineStage` como vocabulario exclusivo del pipeline async; el rule preview queda fuera del enum

- **Ventajas**:
  - `PipelineStage` sigue siendo pequeño, cerrado y con un único significado:
    fase de un `NLPJobRequest` persistido.
  - El rule preview se documenta como lo que realmente es — una capacidad de
    API distinta, sin estado, sin versión registrada, sin FK a
    `knowledge.classifications`.
  - No requiere tocar `NLPJobRequest`, `idempotency_key`, ni los tests que ya
    fijan la partición `SYNC_STAGES`/`ASYNC_STAGES`.
- **Desventajas**: el flujo en prosa necesita una aclaración explícita para no
  sugerir que "Rules" es un stage (ver Consecuencias).

## Decisión

Se adopta la **Opción C**. `PipelineStage` representa solo las fases del
pipeline asíncrono persistido. El rule preview síncrono (`POST /classify`) es
una capacidad de API independiente, advisory-only, que reutiliza `RuleEngine`
pero nunca pasa por `NLPJobRequest`/`PipelineStage`.

`PipelineStage` incorpora un docstring que fija esta decisión, y
`test_rule_preview_is_not_a_pipeline_stage` (`tests/nlp/test_architecture.py`)
bloquea que se agregue un miembro `rules`/`rule_preview` sin revisar
deliberadamente este ADR primero.

## Consecuencias

- `docs/07-ai/contracts.md` separa el diagrama de flujo en dos líneas: una para
  el rule preview síncrono (fuera de la cola), otra para el pipeline async
  completo.
- Cuando 6.7 implemente reglas persistidas en base de datos, `CLASSIFICATION`
  seguirá siendo el único lugar donde una clasificación por reglas se
  persiste y versiona; `POST /classify` puede seguir existiendo como atajo de
  ida y vuelta rápida sin cambiar de significado.
- Ningún código de producción depende de que "Rules" sea un `PipelineStage`;
  si en el futuro se necesita encolar el rule-matching de forma asíncrona
  también, la extensión natural es que pase a ser parte del stage
  `CLASSIFICATION` (vía `StageExecutor`), no un nuevo miembro del enum.
