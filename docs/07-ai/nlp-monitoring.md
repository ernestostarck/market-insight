# NLP Monitoring & Observability (Fase 6.24)

Infraestructura de observabilidad, telemetría Prometheus, dashboards de Grafana y detección continua de Data Drift para los pipelines NLP de MercadoInsight.

---

## 1. Métricas de Prometheus

Ubicación: [`apps/backend/app/nlp/observability/metrics.py`](file:///c:/Users/artut/market-insight/apps/backend/app/nlp/observability/metrics.py)

Todas las métricas están expuestas en el endpoint `/metrics` de la aplicación FastAPI:

| Métrica | Tipo | Etiquetas | Descripción |
| :--- | :--- | :--- | :--- |
| `market_insight_nlp_tenders_processed_total` | Counter | `pipeline_type`, `status` | Cantidad total de licitaciones procesadas por el pipeline NLP (`hybrid`, `rule`, `embeddings`). |
| `market_insight_nlp_processing_duration_seconds` | Histogram | `step` | Latencia por paso del pipeline (`preprocessing`, `classification`, `ner`, `end_to_end`). |
| `market_insight_nlp_errors_total` | Counter | `step`, `error_type` | Errores detectados durante el procesamiento. |
| `market_insight_nlp_confidence_score` | Histogram | `component` | Distribución de los puntajes de confianza (`classifier`, `ner`, `hybrid`). |
| `market_insight_nlp_category_distribution_total` | Counter | `category_code` | Volumen de licitaciones asignadas a cada categoría de la taxonomía. |
| `market_insight_nlp_human_reviews_total` | Counter | `reason` | Casos derivados a la cola de revisión humana (`low_confidence`, `borderline`, `disagreement`). |
| `market_insight_nlp_data_drift_kl_divergence` | Gauge | `baseline_version` | Divergencia Kullback-Leibler calculada contra la distribución base. |

---

## 2. Detección de Data Drift (`DataDriftDetector`)

Ubicación: [`apps/backend/app/nlp/observability/drift.py`](file:///c:/Users/artut/market-insight/apps/backend/app/nlp/observability/drift.py)

### Metodología de Cálculo
El detector utiliza la divergencia de Kullback-Leibler (KL) sobre las distribuciones de frecuencias de categorías observadas vs. la distribución base (Gold Dataset o modelo en producción):

$$D_{KL}(P \parallel Q) = \sum_{x \in \mathcal{X}} P(x) \log \left( \frac{P(x)}{Q(x)} \right)$$

Donde:
- $P(x)$: Distribución de probabilidades observada en el tráfico reciente.
- $Q(x)$: Distribución base de referencia.
- $\epsilon = 10^{-5}$: Suavizado laplaciano/épsilon para evitar división por cero en categorías con cero apariciones en alguno de los conjuntos.

### Umbrales de Alerta
- **$D_{KL} < 0.20$**: Normal. Distribución estable.
- **$0.20 \le D_{KL} < 0.50$**: Leve desplazamiento. Informativo.
- **$0.50 \le D_{KL} < 1.00$**: Advertencia (Warning). Drift moderado detectado.
- **$D_{KL} \ge 1.00$**: Alerta crítica (Alert). Desviación estructural severa; se recomienda reentrenar (`POST /api/v1/ai/models/retrain`).

---

## 3. Configuración de Scraping Prometheus

Ubicación: [`infrastructure/monitoring/prometheus/prometheus.yml`](file:///c:/Users/artut/market-insight/infrastructure/monitoring/prometheus/prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "market-insight-backend"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["backend:8000"]
        labels:
          environment: "production"
          service: "api-backend"

  - job_name: "market-insight-nlp-worker"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["worker:8000"]
        labels:
          environment: "production"
          service: "nlp-worker"
```

---

## 4. Dashboard de Grafana (`nlp_overview.json`)

Ubicación: [`infrastructure/monitoring/grafana/dashboards/nlp_overview.json`](file:///c:/Users/artut/market-insight/infrastructure/monitoring/grafana/dashboards/nlp_overview.json)

El tablero incluye 6 paneles clave diseñados para monitorización en tiempo real:
1. **NLP Processing Throughput**: Tasa de licitaciones procesadas por segundo (`rate(market_insight_nlp_tenders_processed_total[1m])`).
2. **Step Latencies (p95 / p99)**: Cuantiles de duración de preprocesamiento, clasificación y NER (`histogram_quantile(0.95, ...)`).
3. **Classification Confidence Distribution**: Distribución de confianza promedio y percentiles en las predicciones.
4. **Category Distribution**: Desglose dinámico de licitaciones por código de categoría.
5. **Human Review Escalation Rate**: Tasa de licitaciones enviadas a validación manual por motivo.
6. **Data Drift (KL Divergence)**: Indicador de divergencia KL con líneas de umbral a 0.5 (Warning) y 1.0 (Alert).
