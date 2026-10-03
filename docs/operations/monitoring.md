# Manual de Operaciones — Monitoreo y Observabilidad

Este documento proporciona la guía operacional para el monitoreo en tiempo real, tableros de control y gestión de alertas de **MercadoInsight**.

---

## 1. Pila de Observabilidad

| Componente | Rol Principal | Acceso Interno / Puerto |
| :--- | :--- | :--- |
| **Prometheus** | Recolección de métricas cronológicas, evaluación de reglas y alertas | `http://prometheus:9090` |
| **Grafana** | Visualización interactiva y dashboards operativos | `http://localhost:3000` (o `/grafana` en prod) |
| **Alertmanager** | Enrutamiento, silenciamiento y despacho de notificaciones a Slack/Email | `http://alertmanager:9093` |
| **Loki & Promtail** | Agregación e indexación de logs estructurados en JSON | `http://loki:3100` |
| **Sentry** | Detección y agregación de excepciones en tiempo de ejecución (Frontend y Backend) | Cloud / On-Premise |

---

## 2. Dashboards Oficiales en Grafana

Ubicados en `docker/monitoring/grafana/dashboards/`:

1. **`slo-monitoring.json`**:
   - Disponibilidad global de la API (SLO 99.5%).
   - Presupuesto de error (*Error Budget*) restante.
   - Latencias P50, P95 y P99.
2. **`postgresql-monitoring.json`**:
   - Conexiones activas vs. pool máximo (`max_connections`).
   - Uso de memoria compartida y tasa de aciertos de caché (*cache hit ratio* > 99%).
   - Tiempos de ejecución de consultas lentas e impacto de índices HNSW.
3. **`redis-monitoring.json`**:
   - Longitud de colas de Celery (`default`, `etl`, `nlp`, `ai`).
   - Uso de memoria RAM y tasa de desalojo de llaves.
4. **`etl-monitoring.json`**:
   - Estado de últimas corridas (`SUCCESS`, `FAILED`).
   - Volumen de licitaciones y órdenes de compra ingestadas vs. cuarentena.
   - Duración promedio del pipeline por lote.
5. **`nlp-monitoring.json`**:
   - Tasa de licitaciones clasificadas por taxonomía.
   - Confianza media de clasificación e ingresos a la cola de revisión humana.
   - Detección de Data Drift (divergencia Kullback-Leibler).
6. **`rag-monitoring.json`**:
   - Latencia de búsqueda híbrida y generación de respuestas por LLM.
   - Puntuación media de grounding (*fidelidad contextual*).
   - Tasa de tokens consumidos y costos acumulados en USD.
7. **`data-quality-monitoring.json`**:
   - Frescura de datos de ChileCompra (diferencia temporal con respecto a última actualización oficial).
   - Integridad referencial y anomalías estadísticas detectadas.
8. **`logs-explorer.json`**:
   - Explorador centralizado de logs con filtros por nivel (`ERROR`, `WARNING`, `INFO`), contenedor y `request_id`.

---

## 3. Gestión de Alertas

- Las reglas de alerta están definidas en `docker/monitoring/prometheus/rules/` (`api.yml`, `database.yml`, `etl.yml`, `nlp.yml`, `ai-cost.yml`).
- Procedimiento para silenciar una alerta durante mantenimiento planificado:
  1. Ingresar a Alertmanager: `http://localhost:9093/#/silences`.
  2. Crear nuevo silencio especificando el matcher (ejemplo: `alertname="DatabaseHighConnections"`).
  3. Definir ventana de tiempo y motivo del mantenimiento.
