# ADR 0001 — Workers del ETL: Celery vs ARQ

- **Fecha**: 2026-08-07
- **Fase**: 3.11 — Orquestación
- **Estado**: Aceptado

## Contexto

El pipeline de ETL (extract → validate → transform → load) es un proceso pesado que no debe
ejecutarse dentro del proceso de FastAPI. La fase 3.11 establece una arquitectura de cola:

```text
FastAPI
   │ ordena
   ▼
Redis / Queue
   │
   ▼
ETL Worker
```

El proyecto ya cuenta con **Redis** (broker/backend de mensajería) y con un esqueleto Celery en
`app/worker/celery_app.py`. Debemos decidir si consolidamos **Celery** o adoptamos **ARQ** como
sistema de tasks/worker.

## Opciones consideradas

### Celery (>= 5.4)
- **Ventajas**:
  - Framework de tasks maduro y ampliamente adoptado.
  - `celery beat` para programación periódica (incremental diario) con `beat_schedule`.
  - Retries integrados (`task.retry`), bind de tasks, prioridades, routing por cola.
  - Soporte multi-worker y monitoreo (flower).
  - Ya está instalado en `pyproject.toml` y configurado con `REDIS_URL`.
- **Desventajas**:
  - Mayor superficie / dependencias.
  - En versiones antiguas acoplado a kombu/amqp (aunque funciona bien con Redis).

### ARQ
- **Ventajas**:
  - Ligero, asyncio nativo, curva baja.
  - Muy bueno para flujos 100% async.
- **Desventajas**:
  - No trae beat/scheduling incorporado (hay que componer con `asyncio` + aparte).
  - Menos maduro que Celery para *retries*, *result backend*, *prioridades* y *monitoreo*.
  - No está instalado en el stack actual.

## Diagnóstico de nuestro caso de uso

El ETL es un job **periódico** (incremental diario/horario) más un job **bajo demanda**
(re-sync de un recurso). Los requisitos que importan aquí:

1. **Scheduling periódico** (celery beat) → Celery lo resuelve de serie.
2. **Reintentos ante fallos parciales** → Celery tiene retry nativo.
3. **Observabilidad del estado de tasks** (result backend) → Celery con Redis backend.
4. **Aislamiento del proceso FastAPI** → ambos lo garantizan.

## Decisión

Mantener **Celery** como sistema de workers y orquestación del ETL.

Razones:

- Ya forma parte del stack (dependencia instalada y `celery_app` presente), lo que evita
  introducir una dependencia nueva sin beneficio claro.
- `celery beat` cubre el caso de **incremental loads** de forma declarativa.
- El retry nativo es directamente útil para la fase 3.12 (error handling).
- ARQ no aporta valor diferencial aquí y añadiría scheduling manual.

Se documenta que revisaremos ARQ únicamente si el equipo migra toda la capa de workers a un
modelo puramente asíncrono sin necesidad de beat/retry/monitoreo.

## Consecuencias

- `app/worker/celery_app.py` es el punto de entrada del worker.
- La programación (`beat_schedule`) y las tareas se centralizan en `app/etl/orchestration/`.
- Los workers se lanzan con `celery -A app.worker.celery_app worker` y beat con
  `celery -A app.worker.celery_app beat`.
- La decisión queda trazada en el repositorio (este ADR).

