# Worker Asíncrono NLP (Fase 6.20)

El **Worker Asíncrono NLP** proporciona el entorno de ejecución desacoplado para el pipeline de procesamiento de lenguaje natural, clasificación y generación de embeddings sobre licitaciones de compras públicas en background.

---

## 1. Arquitectura y Componentes

El worker está desacoplado de la API web mediante **Celery** y colas en **Redis**:

```
[ FastAPI Endpoint /api/v1/ai/jobs ]
               │
               ▼  (job enqueue)
     [ Redis Queue: 'nlp' ]
               │
               ▼  (consume task)
   [ Worker: nlp_worker.py ]
               │
       ┌───────┴────────┐
       ▼                ▼
[ JobTracker ]    [ execute_nlp_job ]
 (Redis Cache)    ├── PreprocessingStageExecutor
                  ├── ClassificationStageExecutor
                  └── EmbeddingsStageExecutor
                        │
                        ▼
            [ PostgreSQL: knowledge.nlp_jobs ]
```

### Componentes Principales:
1. **`app/worker/nlp_tasks.py`**:
   - `process_nlp_job`: Tarea Celery para procesar una licitación individual con idempotencia, telemetría y reintentos exponenciales.
   - `process_nlp_batch`: Tarea Celery para procesar lotes de licitaciones agregando estadísticas (total, exitosas, fallidas, duración).
2. **`app/worker/job_tracker.py` (`JobTracker`)**:
   - Abstracción de estado y caché sobre Redis.
   - Claves de Redis:
     - `nlp:idempotency:{idempotency_key}`: TTL 24 horas (`86400s`). Almacena el resultado para saltar ejecuciones duplicadas idénticas.
     - `nlp:job:{task_id}`: TTL 2 horas (`7200s`). Almacena el estado actual (`queued`, `running`, `succeeded`, `failed`) y duración.
   - Degradación elegante: si Redis no está disponible o falla la conexión, opera como no-op seguro sin interrumpir la ejecución.
3. **`app/worker/nlp_worker.py`**:
   - Script ejecutable y punto de entrada para el worker daemon.
   - Lanza Celery configurado con `concurrency` configurable, cola `nlp`, logging estructurado y modo optimizado para inferencia.

---

## 2. Idempotencia y Deduplicación

Para evitar el re-procesamiento redundante de licitaciones sin cambios:

### Clave de Idempotencia:
```
{licitacion_id}:{text_hash}:{taxonomy_version}:{dictionary_version}:{model_version}:{embedding_model_version}
```

### Flujo de Verificación:
1. **Caché Redis (`JobTracker.get_idempotent_result`)**:
   - Si la clave ya está en Redis con estado `succeeded`, se retorna inmediatamente el resultado cacheado con bandera `cached: True`.
2. **PostgreSQL (`knowledge.nlp_jobs`)**:
   - Si Redis expira pero PostgreSQL ya tiene registrado un resultado exitoso para esa misma clave de idempotencia, se retorna `result_summary`.
3. **Ejecución del Pipeline**:
   - Si no existe registro previo, se ejecuta el pipeline completo (`execute_nlp_job`) y se persisten los resultados tanto en Redis como en PostgreSQL.

---

## 3. Persistencia en Base de Datos (`knowledge.nlp_jobs`)

Tabla creada mediante la migración Alembic `20260828_0015_create_knowledge_nlp_jobs.py`:

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `UUID` (PK) | Identificador único del registro de trabajo. |
| `celery_task_id` | `VARCHAR(128)` | ID de la tarea en Celery (indexado). |
| `idempotency_key` | `VARCHAR(256)` | Clave compuesta única (indexado). |
| `licitacion_id` | `INTEGER` | ID de la licitación en `core.licitacion`. |
| `status` | `VARCHAR(32)` | Estado: `queued`, `running`, `succeeded`, `failed`, `partial`. |
| `duration_seconds` | `NUMERIC(10, 4)` | Tiempo de ejecución total en segundos. |
| `completed_stages` | `JSONB` | Lista de etapas completadas exitosamente. |
| `pending_stages` | `JSONB` | Lista de etapas pendientes o no ejecutadas. |
| `error` | `JSONB` | Detalle del error (`stage`, `code`, `message`). |
| `result_summary` | `JSONB` | Resumen estructurado del resultado del pipeline. |
| `retries` | `INTEGER` | Número de reintentos efectuados. |
| `created_at` | `TIMESTAMPTZ` | Marca temporal de creación. |
| `updated_at` | `TIMESTAMPTZ` | Marca temporal de última actualización. |

---

## 4. Reintentos y Tolerancia a Fallos

- **Acks Late**: `acks_late=True` asegura que la tarea no se reconoce en Redis hasta que finaliza con éxito o se maneja explícitamente el fallo.
- **Backoff Exponencial**:
  - Reintentos automáticos ante excepciones transitorias (ej. fallos de red o base de datos).
  - Delay: `countdown = 2 ** retries` (1s, 2s, 4s...) hasta `max_retries=3`.
- **Registro de Errores Estructurado**:
  - Los fallos registran el objeto `JobError` (`PipelineStage`, código de error y mensaje amigable) para auditoría.

---

## 5. Procesamiento por Lotes (`process_nlp_batch`)

Permite la ingesta masiva de licitaciones (ej. cargas nocturnas o re-clasificación por nueva versión de taxonomía):

```python
payload = [
    {"licitacion_id": 100, "text_hash": "...", "versions": {...}},
    {"licitacion_id": 101, "text_hash": "...", "versions": {...}},
]
result = process_nlp_batch.apply_async(args=[payload], queue="nlp")
```

Respuesta estructurada del lote:
```json
{
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "duration_seconds": 1.4521,
  "results": [...]
}
```

---

## 6. Ejecución del Worker

Para iniciar el worker en desarrollo o producción:

```bash
# Vía script dedicado con argumentos
python -m app.worker.nlp_worker --concurrency=2 --loglevel=INFO

# O directamente mediante Celery CLI
celery -A app.worker.celery_app worker -Q nlp -l info -c 2
```
