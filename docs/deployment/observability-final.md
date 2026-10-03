# Observabilidad Final y Telemetría — MercadoInsight

Este documento detalla la integración consolidada del stack de observabilidad de **MercadoInsight**, unificando métricas, registros, trazas distribuidas, seguimiento de excepciones y tableros operacionales (Fase 10.17).

---

## 1. Arquitectura de Observabilidad Unificada

```text
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  FastAPI API │     │ Celery Worker│     │ Exporters    │
  │ (Metrics/OTel│     │ (Metrics/    │     │ (Postgres /  │
  │  /Sentry)    │     │  Tracing)    │     │  Redis)      │
  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│    Prometheus    │ │       Loki       │ │ OpenTelemetry  │
│  (Métricas TSDB) │ │ (Logs JSON/Trace)│ │   Collector    │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                     ┌──────────────────┐
                     │     Grafana      │
                     │  (Visualización  │
                     │   Consolidada)   │
                     └──────────────────┘
```

---

## 2. Componentes del Stack

| Componente | Versión | Rol | Mecanismo de Seguridad |
| :--- | :--- | :--- | :--- |
| **Prometheus** | `v2.53.0` | Recolección de series temporales (`/metrics` cada 15s). | Red privada interna, sin puerto publicado al host. |
| **Grafana** | `11.0.0` | Visualización en tiempo real y dashboards analíticos. | Detrás de NGINX (`/grafana/`) con HTTP Basic Auth + login admin. |
| **Alertmanager** | `v0.27.0` | Enrutamiento, deduplicación y notificación de alertas. | Detrás de NGINX (`/alertmanager/`) con Basic Auth y secret tokens. |
| **Loki + Promtail**| `3.0.0` | Ingesta, indexación por etiquetas y consulta de logs JSON. | Red privada interna, buffers locales y rotación de archivos. |
| **Sentry** | SDK 2.x | Captura de excepciones en Python y reporte de releases. | Scrubbing exhaustivo de PII y credenciales (`before_send`). |
| **OpenTelemetry** | `0.104.0` | Tracing distribuido de peticiones HTTP y tareas Celery. | Red interna OTLP gRPC en puerto 4317. |

---

## 3. Catálogo de Métricas Clave

### 3.1 API HTTP
* `http_requests_total`: Conteo total por método, ruta y código de estado.
* `http_request_duration_seconds`: Histograma de latencia con buckets calibrados para P95 y P99.
* `http_errors_total`: Conteo de errores 4xx (`client_error`) y 5xx (`server_error`).

### 3.2 Almacenamiento e Infraestructura
* **PostgreSQL** (`postgres-exporter`): Conexiones activas, bloqueos (`pg_locks`), cache hit ratio y tamaño de bases de datos.
* **Redis** (`redis-exporter`): Memoria utilizada, conexiones de clientes, tasa de aciertos (`keyspace_hits`) y comandos por segundo.
* **Recursos de Contenedores** (`cAdvisor`): Consumo de CPU, memoria RAM y ancho de banda de red por contenedor.

### 3.3 Pipelines ETL y Calidad de Datos
* `etl_runs_total`: Corridas por pipeline (`status: success | failed | running`).
* `etl_records_processed_total`: Registros leídos, insertados y actualizados.
* `etl_duration_seconds`: Duración de las ingestas.
* `data_freshness_seconds`: Antigüedad de la última licitación procesada respecto al tiempo actual.
* `data_quality_score`: Puntaje reproducible de calidad de datos (0 a 100).
* `duplicate_records_total`: Registros duplicados interceptados.

### 3.4 Inteligencia Artificial y RAG (Fase 9)
* `ai_rag_requests_total`: Peticiones RAG por intención y estrategia de recuperación.
* `ai_rag_latency_seconds`: Latencia desglosada por etapas (recuperación, reranker, generación).
* `ai_grounding_score`: Distribución de fundamentación fáctica (detección de alucinaciones).
* `ai_guardrail_blocks_total`: Bloqueos de seguridad por inyección de prompts o fuera de ámbito.
* `ai_rag_tokens_total`: Tokens de entrada y salida consumidos por modelo.
* `ai_rag_cost_usd_total`: Gasto monetario estimado en USD por modelo e intención.
* `ai_costly_queries_total`: Consultas catalogadas como excesivamente costosas.
* `ai_feedback_total`: Retroalimentación de usuarios (pulgar arriba/abajo).

---

## 4. Dashboards Preconfigurados en Grafana

Todos los tableros se encuentran versionados en [`docker/monitoring/grafana/dashboards/`](file:///c:/Users/artut/market-insight/docker/monitoring/grafana/dashboards/):

1. **`market-insight-overview.json`**: Salud global del sistema, disponibilidad HTTP, RPS y saturación.
2. **`etl-monitoring.json`**: Estado de pipelines ETL, registros procesados y latencia de ingesta.
3. **`data-quality-monitoring.json`**: Métricas de calidad de datos, duplicados y reglas de validación.
4. **`rag-monitoring.json`**: Consultas RAG, latencias de modelos, gasto en tokens, grounding y feedback.
5. **`nlp-monitoring.json`**: Desempeño de clasificación, embeddings y cola de revisión humana.
6. **`postgresql-monitoring.json` & `redis-monitoring.json`**: Métricas de base de datos y caché.
7. **`slo-monitoring.json`**: Presupuesto de error (Error Budgets) y cumplimiento de SLOs.
8. **`logs-explorer.json`**: Explorador de logs estructurados indexados en Loki.
