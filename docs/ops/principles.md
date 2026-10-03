# Principios de implementación de la observabilidad (Fase 8)

Cada principio tiene un mecanismo concreto y un test que falla si se rompe
(`apps/backend/tests/test_observability_principles.py`).

| # | Principio | Mecanismo | Dónde |
|---|-----------|-----------|-------|
| 1 | No alertar solo porque un indicador cambió | Toda alerta lleva severidad, resumen y descripción operacional; las que solo miran volumen son `info` y no notifican | `prometheus/rules/*.yml` |
| 2 | Cambio normal del negocio ≠ falla operacional | La falla se define por señales operacionales (`etl_records_failed_total`, `etl_last_success_timestamp`, `data_freshness_seconds`, `up`), nunca por volumen | `ETLIngestionVolumeDrop` (info) vs `ETLFailed` / `ETLStale` / `DataFreshness*` |
| 3 | Menos licitaciones ≠ caída de ChileCompra | Ningún texto de alerta afirma que ChileCompra está caído a partir de datos; `/system/status` solo sugiere el upstream si la sonda técnica de ChileCompra falla | test de textos + `availability.data.reasons` |
| 4 | Disponibilidad técnica y de datos por separado | `/api/v1/system/status` devuelve `availability.technical` y `availability.data` independientes; un dato viejo nunca vuelve el estado global `unhealthy` | `app/api/v1/endpoints/system.py` |
| 5 | Usar `data_freshness` para detectar problemas de actualización | El gauge `data_freshness_seconds` se recalcula cada 60 s desde el último `etl.etl_runs` exitoso (workers y API no comparten memoria); umbrales 18 h / 36 h idénticos en código y reglas | `app/monitoring/data_freshness.py`, `rules/data-quality.yml` |
| 6 | Métricas reales antes de umbrales definitivos | Recording rules `calibration:*` registran el comportamiento observado; los umbrales actuales son provisionales | `rules/calibration.yml` |
| 7 | Herramientas de observabilidad protegidas | Producción publica solo nginx; Grafana y Alertmanager tras basic auth; `/metrics` devuelve 403; Prometheus, pgAdmin y RedisInsight no se exponen; secretos sin default | `docker-compose.prod.yml`, `docker/nginx/prod/` |
| 8 | Secretos fuera de logs y observabilidad | `redact_text` / `redact_value` sobre mensaje, error, traza y `extra` (anidado) en logs JSON y consola; mismo filtro en eventos Sentry (mensajes, excepciones, breadcrumbs) y en alertas | `app/core/logging.py`, `app/core/sentry.py`, `app/monitoring/alerts.py` |
| 9 | Trazabilidad con `X-Request-ID` | nginx conserva o genera el ID; la API lo valida (`[A-Za-z0-9._-]{1,128}`, si no genera un UUID) y lo devuelve; lo llevan logs, Sentry y spans; viaja a Celery como header | `middleware.py`, `worker/tracing.py`, `nginx/prod` |
| 10 | Métricas de infraestructura, aplicación, datos y NLP separadas | Prefijo por capa (`http_`, `etl_`/`data_`/`duplicate_`/`invalid_`, `nlp_`, exporters); cada archivo de reglas solo lee su capa | tests de prefijos y de reglas |

## Cómo usar `availability`

```json
"availability": {
  "technical": {"status": "healthy", "reasons": []},
  "data": {"status": "unhealthy", "reasons": ["freshness critical: ChileCompra is reachable, so look at the ETL pipeline"]}
}
```

- `technical`: API, PostgreSQL, Redis, storage y alcance de ChileCompra.
- `data`: frescura y score de calidad.
- Que el volumen de licitaciones baje no cambia ninguna de las dos capas.

## Calibración de umbrales

Los umbrales de `rules/*.yml` son **provisionales**. Antes de fijarlos como definitivos,
con al menos 14 días de tráfico real, comparar cada uno con su serie de `calibration.yml`:

| Umbral | Serie observada |
|--------|-----------------|
| `DataFreshnessWarning` / `Critical` (18 h / 36 h) | `calibration:data_freshness_seconds:p95_7d`, `:max_7d` |
| `DataQualityScoreDegraded` / `Critical` (95 / 85) | `calibration:data_quality_score:min_7d` |
| `HighAPILatencyP95` (0.5 s) | `calibration:http_request_duration_seconds:p95_1d` |
| `HighAPIErrorRate5xx` (5 %) | `calibration:http_error_ratio:max_7d` |
| `ETLDurationTooLong` (30 min) | `calibration:etl_duration_seconds:p95_7d` |
| `NLPLowConfidenceSurge` (30 %) | `calibration:nlp_low_confidence_ratio:avg_7d` |

Criterio: un umbral debe quedar por encima del comportamiento sano observado
(p95/max) y por debajo de lo que ya dañaría el SLO. Si la serie sana lo supera, el umbral
genera ruido y se sube; si nunca se acerca, se puede endurecer. Registrar el cambio en `slo.md`.
