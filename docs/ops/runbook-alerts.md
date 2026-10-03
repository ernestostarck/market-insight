# Manual Operativo de Respuesta ante Alertas de Producción (Runbook)

Este documento detalla los procedimientos estándar de diagnóstico, triaje y mitigación para las alertas de producción de **MercadoInsight**. Cada alerta `critical` tiene su procedimiento bajo su nombre exacto (un test lo verifica); las de advertencia e informativas están resumidas al final.

**Primer paso ante cualquier alerta de datos**: consultar `GET /api/v1/system/status` y separar `availability.technical` (¿puede la plataforma servir?) de `availability.data` (¿los datos están al día?). Que baje el volumen de licitaciones publicadas **no** es una falla ni implica que ChileCompra esté caído; la disponibilidad técnica del upstream se mide con `chilecompra_up`.

---

## Matriz de Severidad y Canales de Notificación

| Alerta | Severidad | Tiempo Máx. Respuesta (SLA) | Canal Principal |
| :--- | :--- | :--- | :--- |
| **APIUnavailable** | `critical` | 5 minutos | Webhook crítico / Email admin |
| **PostgreSQLUnavailable** | `critical` | 5 minutos | Webhook crítico / Email admin |
| **RedisUnavailable** | `critical` | 5 minutos | Webhook crítico / Email admin |
| **ETLFailed** | `critical` | 15 minutos | Data Engineering Webhook |
| **ETLStale** | `warning` | 1 hora | Email + webhook |
| **DataFreshnessCritical** | `critical` | 30 minutos | Email + webhook |
| **ETLHighErrorRate** | `critical` | 15 minutos | Email + webhook |
| **DataQualityScoreCritical** | `critical` | 1 hora | Email + webhook |
| **InstanceDown** | `critical` | 10 minutos | Email + webhook |
| **NLPWorkerDown** | `critical` | 15 minutos | Email + webhook |
| **NLPHighErrorRate** | `critical` | 15 minutos | Email + webhook |
| **SLOAvailabilityBurnRateCritical** | `critical` | 10 minutos | Email + webhook |
| **HighAPIErrorRate5xx** | `critical` | 10 minutos | Webhook crítico / Sentry |
| **HighAPILatencyP95** | `warning` | 30 minutos | Backend Webhook |
| **PostgreSQLConnectionSaturation** | `critical` | 15 minutos | Database Webhook |
| **RedisMemoryPressure** | `warning` | 1 hora | DevOps Webhook |
| **NLPEmbeddingModelFailure** | `critical` | 15 minutos | ML Engineering Webhook |
| **DataQualityScoreDegraded** | `warning` | 2 horas | Data Engineering Webhook |

---

## Procedimientos Detallados por Alerta

### 1. `APIUnavailable`
- **Síntoma**: El contenedor backend no responde a los healthchecks (`up{job="backend"} == 0`).
- **Diagnóstico**:
  ```bash
  docker compose ps backend
  docker compose logs --tail=100 backend
  curl -I http://localhost:8000/health/live
  ```
- **Mitigación**:
  1. Si el contenedor se cerró por OOM (Out Of Memory), revise el consumo en Grafana y aumente el límite de memoria.
  2. Si el proceso está congelado esperando I/O, reinicie el servicio: `docker compose restart backend`.
  3. Verifique en Sentry si una excepción no controlada provocó el reinicio de Uvicorn.

---

### 2. `PostgreSQLUnavailable`
- **Síntoma**: El motor de base de datos no acepta conexiones ni responde a las sondas.
- **Diagnóstico**:
  ```bash
  docker compose ps postgres
  docker compose exec postgres pg_isready -U market_insight -d market_insight
  docker compose logs --tail=100 postgres
  ```
- **Mitigación**:
  1. Verifique el espacio disponible en disco: `df -h`. Si el disco está al 100%, amplíe el volumen.
  2. Si PostgreSQL está en recuperación tras caída, espere a que termine el replay de WAL.
  3. Reinicie el servicio: `docker compose restart postgres`.

---

### 3. `RedisUnavailable`
- **Síntoma**: Redis exporter o la API no logran comunicarse con Redis (`redis-cli ping` falla).
- **Diagnóstico**:
  ```bash
  docker compose exec redis redis-cli -a "$REDIS_PASSWORD" ping
  docker compose logs --tail=50 redis
  ```
- **Mitigación**:
  1. Reinicie el servicio: `docker compose restart redis`.
  2. Compruebe si la persistencia RDB/AOF falló por falta de permisos o espacio.

---

### 4. `ETLFailed`
- **Síntoma**: Se detectaron registros o lotes fallidos en la ingesta de ChileCompra.
- **Diagnóstico**:
  1. Revise en PostgreSQL la tabla de ejecuciones:
     ```sql
     SELECT run_id, pipeline, status, records_failed, error_message, started_at
     FROM etl.etl_runs
     ORDER BY started_at DESC LIMIT 5;
     ```
  2. Consulte en Grafana Loki los registros del pipeline:
     `{pipeline="licitaciones"} | json | level="ERROR"`
- **Mitigación**:
  1. Si el fallo se debe a timeout de la API de ChileCompra, verifique la conectividad externa.
  2. Si la falla es por validación de esquema, ajuste el transformer correspondiente.
  3. Lance un retry manual del run fallido desde el endpoint o Celery task.

---

### 5. `ETLStale`
- **Síntoma**: No se ha registrado ninguna sincronización exitosa en más de 24 horas.
- **Diagnóstico**:
  1. Verifique que el scheduler y el worker de ETL estén en ejecución:
     ```bash
     docker compose ps etl-beat etl-worker
     docker compose logs --tail=50 etl-worker
     ```
  2. Verifique la métrica: `time() - etl_last_success_timestamp`.
- **Mitigación**:
  1. Reinicie los workers si las tareas programadas están encoladas sin procesar.
  2. Ejecute una sincronización puntual vía API: `POST /api/v1/etl/sync/licitaciones`.

---

### 6. `DataFreshnessCritical` (y `DataFreshnessWarning`)
- **Síntoma**: `data_freshness_seconds` supera 18 h (`DataFreshnessWarning`) o 36 h (`DataFreshnessCritical`). Se mide desde la última ejecución ETL exitosa de `licitaciones`; los umbrales toleran el ciclo de publicación de días hábiles y los fines de semana.
- **Diagnóstico**:
  1. Consulte la última ejecución exitosa:
     ```sql
     SELECT max(finished_at) FROM etl.etl_runs WHERE pipeline = 'licitaciones' AND status IN ('succeeded','success');
     ```
  2. `GET /api/v1/system/status`: si `components.chilecompra` está sano, el problema está en el pipeline (revise `etl-worker`/`etl-beat`); si está caído (`chilecompra_up == 0`), la causa probable es el upstream. Un feriado o fin de semana con poca publicación no cuenta como falla.
- **Mitigación**:
  1. Valide el ticket de la API de ChileCompra (`CHILECOMPRA_API_KEY`).
  2. Verifique si la API de ChileCompra está en mantenimiento programado.

---

### 7. `HighAPIErrorRate5xx`
- **Síntoma**: Más del 5% de las solicitudes HTTP responden con códigos 5xx.
- **Diagnóstico**:
  1. Abra **Sentry** y filtre por el ambiente afectado para ubicar el issue más reciente.
  2. Filtre en Loki: `{service="market-insight-backend"} | json | level="ERROR"`.
- **Mitigación**:
  1. Si un endpoint específico está fallando, verifique si se trata de un parámetro mal manejado o caída de una dependencia externa.
  2. Si es producto de un despliegue reciente, ejecute un rollback a la versión previa estable.

---

### 8. `HighAPILatencyP95`
- **Síntoma**: El percentil 95 de tiempo de respuesta supera los 500 ms.
- **Diagnóstico**:
  1. Abra el dashboard de Grafana **API Performance** y localice el endpoint con mayor latencia.
  2. Verifique en el dashboard de PostgreSQL si hay consultas lentas (`SlowQueriesDetected`).
  3. Ejecute en PostgreSQL:
     ```sql
     SELECT pid, now() - query_start AS duration, query
     FROM pg_stat_activity
     WHERE state != 'idle' ORDER BY duration DESC LIMIT 5;
     ```
- **Mitigación**:
  1. Cancele consultas bloqueadas o anormalmente largas: `SELECT pg_cancel_backend(pid);`.
  2. Agregue índices si se detectan sequential scans masivos.

---

### 9. `PostgreSQLConnectionSaturation`
- **Síntoma**: Conexiones activas superan el 85% de `max_connections`.
- **Diagnóstico**:
  ```sql
  SELECT count(*), state, usename FROM pg_stat_activity GROUP BY state, usename;
  ```
- **Mitigación**:
  1. Finalice conexiones huérfanas en estado `idle in transaction`.
  2. Revise si hay fugas de conexiones en el backend (sesiones de SQLAlchemy no cerradas).
  3. Si la carga es legítima, aumente `max_connections` en `postgresql.conf`.

---

### 10. `RedisMemoryPressure`
- **Síntoma**: Redis excede el 85% de la memoria máxima permitida (`maxmemory`).
- **Diagnóstico**:
  ```bash
  docker compose exec redis redis-cli -a "$REDIS_PASSWORD" info memory
  docker compose exec redis redis-cli -a "$REDIS_PASSWORD" --bigkeys
  ```
- **Mitigación**:
  1. Verifique la política de desalojo: debe estar configurada en `allkeys-lru` o `volatile-lru`.
  2. Elimine claves temporales de prueba o incremente `maxmemory` en `redis.conf`.

---

### 11. `NLPEmbeddingModelFailure` (y `NLPHighErrorRate`)
- **Síntoma**: Fallos reiterados al generar embeddings (`nlp_embedding_failures_total`) o errores NLP sostenidos (`nlp_errors_total` por `stage` y `error_code`).
- **Diagnóstico**:
  1. Revise los registros del worker de NLP:
     `docker compose logs --tail=100 nlp-worker`
  2. Verifique si el contenedor se quedó sin memoria RAM para cargar el modelo de Sentence Transformers.
- **Mitigación**:
  1. Reinicie el worker de NLP: `docker compose restart nlp-worker`.
  2. Asegure que el directorio de caché de modelos `/root/.cache/huggingface` tenga espacio y permisos.

---

### 12. `DataQualityScoreDegraded` (y `DataQualityScoreCritical`)
- **Síntoma**: `data_quality_score` bajo 95 (`DataQualityScoreDegraded`) o bajo 85 (`DataQualityScoreCritical`). El score pondera las violaciones por lote e incluye como peor caso los registros rechazados por validación (`failed_validation`).
- **Diagnóstico**:
  1. Ingrese al dashboard **Data Quality Monitoring** en Grafana.
  2. Identifique el tipo de infracción predominante: `missing_id`, `invalid_rut`, `invalid_date`, `invalid_amount` o `missing_supplier`.
  3. Examine en Loki los registros con la etiqueta `event="data_quality_violation"`.
- **Mitigación**:
  1. Si un organismo comprador cambió la estructura de los campos en las respuestas JSON de ChileCompra, ajuste la regla de normalización en el pipeline ETL.
  2. Si se trata de datos anómalos aislados, documente la excepción en el registro de calidad.

---

### 13. `ETLHighErrorRate`
- **Síntoma**: Más del 5 % de los registros procesados fallan (`etl_records_failed_total` / `etl_records_processed_total`).
- **Diagnóstico**: igual que `ETLFailed` (§4); compare `records_failed` por `pipeline` en `etl.etl_runs` para ver si es un recurso o todos.
- **Mitigación**: si es un solo recurso, revise su transformer/validator y la cuarentena; si son todos, sospeche del upstream (`chilecompra_up`) o de un cambio de esquema.

---

### 14. `InstanceDown`
- **Síntoma**: Prometheus no puede scrapear un `job` (`up == 0`) por más de 1 minuto. La etiqueta `job` indica cuál: `backend`, `postgres-exporter`, `redis-exporter`, `cadvisor`, `nlp-worker`, `etl-worker`.
- **Diagnóstico**: `docker compose ps <servicio>` y `docker compose logs --tail=100 <servicio>`.
- **Mitigación**: reinicie el servicio; si es un exporter, verifique credenciales y red. Si es un worker, revise memoria (`docker stats`) y conectividad a Redis.

---

### 15. `NLPWorkerDown`
- **Síntoma**: `up{job="nlp-worker"} == 0`: el worker no responde en su puerto de métricas (8000).
- **Diagnóstico**: `docker compose ps nlp-worker`; `docker compose logs --tail=100 nlp-worker`; `curl http://nlp-worker:8000/metrics` desde la red interna.
- **Mitigación**: `docker compose restart nlp-worker`. Las tareas encoladas en Redis no se pierden (`acks_late`).

---

### 16. `SLOAvailabilityBurnRateCritical`
- **Síntoma**: el presupuesto de errores de disponibilidad se consume a más de 14,4× (ver `slo.md`).
- **Diagnóstico**: proceda como `HighAPIErrorRate5xx` (§7) y `APIUnavailable` (§1); el dashboard **SLO Monitoring** muestra la ventana afectada.
- **Mitigación**: mitigue la causa raíz; si hubo un despliegue reciente, revierta.

---

## Alertas de advertencia e informativas

No requieren respuesta inmediata; se revisan en horario laboral.

| Alerta | Qué significa | Primera acción |
| :--- | :--- | :--- |
| `HighAPILatencyP95` / `HighAPILatencyP99` | Latencia sobre 0,5 s / 1,5 s | Dashboard **API**; consultas lentas en PostgreSQL |
| `ETLDurationTooLong` | Ciclo ETL sobre 30 min | Volumen del lote y latencia de la API de ChileCompra |
| `AbnormalDuplicateRecords` / `HighInvalidRecordsRate` | Repunte de duplicados o registros inválidos | Dashboard **Data Quality**; motivo dominante en `invalid_records_total{reason}` |
| `ETLIngestionVolumeDrop` (`info`) | Menos registros leídos que el promedio. **No es una falla**: puede ser un ciclo normal del mercado | Solo escalar si coincide con `ETLFailed`, `ETLStale` o `DataFreshness*` |
| `NLPLowConfidenceSurge` | Más del 30 % de clasificaciones con confianza < 0,70 | Dashboard **NLP**. Un cambio de distribución no implica por sí solo *model drift* (ver `docs/08-nlp-monitoring-drift-guidance.md`) |
| `HostHighCpuLoad` / `ContainerMemoryPressure` | Recursos sobre 85 % | `docker stats`; ajuste de límites |
| `PostgreSQLDeadlocksDetected` / `RedisBlockedClients` | Bloqueos en la base o en Redis | Logs del motor; consultas o clientes involucrados |
| `SLOLatencyBudgetExhaustion` / `SLOETLSuccessRateDegraded` / `SLODataFreshnessDegraded` | Presupuesto de error de un SLO en riesgo | `slo.md`; dashboard **SLO Monitoring** |
