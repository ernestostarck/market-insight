# Service Level Objectives (SLO) & Service Level Indicators (SLI) — MercadoInsight

Este documento establece formalmente los **Indicadores de Nivel de Servicio (SLI)**, los **Objetivos de Nivel de Servicio (SLO)** y la gestión de **Presupuestos de Error (Error Budgets)** para la plataforma **MercadoInsight**.

Los umbrales han sido calibrados considerando la arquitectura del sistema, las llamadas a la API de ChileCompra/Mercado Público y el ciclo operacional de las compras públicas en Chile.

---

## 1. Resumen Ejecutivo de SLOs

| Indicador (SLI) | Dimensión | Objetivo (SLO) | Ventana Móvil | Presupuesto de Error (Error Budget) | Severidad de Alerta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API Availability** | Confiabilidad HTTP | $\ge 99.5\%$ | 30 días | $0.5\%$ ($\sim 3.6$ horas de indisponibilidad) | Crítica ($14.4\times$ burn) |
| **P95 API Latency (Standard)** | Rendimiento CRUD/API | $\le 300\text{ ms}$ ($0.30\text{ s}$) | 30 días | $5\%$ requests $> 300\text{ms}$ | Advertencia |
| **P95 API Latency (Analytics)** | Agregaciones/Marts | $\le 800\text{ ms}$ ($0.80\text{ s}$) | 30 días | $5\%$ requests $> 800\text{ms}$ | Advertencia |
| **ETL Pipeline Success Rate** | Ingesta y normalización | $\ge 98.0\%$ | 30 días | $2.0\%$ ejecuciones fallidas | Crítica ($> 5\%$ fallos) |
| **Data Freshness Compliance** | Antigüedad de datos | $\ge 95.0\%$ del tiempo $\le 24\text{ h}$ | 30 días | $5.0\%$ del tiempo $> 24\text{h}$ | Advertencia ($\le 18\text{h}$ normal) |

---

## 2. Definición Detallada de SLIs y Fórmulas PromQL

### 2.1 API Availability

- **Definición**: Proporción de solicitudes HTTP atendidas exitosamente (cualquier código distinto de error del servidor `5xx`) sobre el total de solicitudes recibidas en la API.
- **Métrica Prometheus**: `http_requests_total`
- **Fórmula SLI (PromQL instantáneo 5m)**:
  ```promql
  sum(rate(http_requests_total{status!~"5.."}[5m]))
  /
  sum(rate(http_requests_total[5m]))
  ```
- **Recording Rule**: `sli:http_availability:ratio_rate5m`
- **Error Budget (30 días)**:
  - En un mes de 30 días ($43,200$ minutos), un SLO de $99.5\%$ permite un máximo de **$216$ minutos ($3.6$ horas)** acumuladas de respuestas $5\text{xx}$ antes de agotar el presupuesto.

---

### 2.2 P95 API Latency

- **Definición**: Tiempo de respuesta en el percentil 95 para solicitudes procesadas por la API FastAPI.
- **Métrica Prometheus**: `http_request_duration_seconds_bucket`
- **Fórmula SLI (PromQL instantáneo 5m)**:
  ```promql
  histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
  ```
- **Recording Rule**: `sli:http_latency_p95:seconds_rate5m`
- **Objetivos por Categoría de Endpoint**:
  1. *Transaccionales y Búsqueda Directa* (`/api/v1/licitaciones`, `/api/v1/auth`, `/api/v1/system/status`): $\le 300\text{ ms}$.
  2. *Analíticos y Agregaciones DW* (`/api/v1/analytics/*`, reportes): $\le 800\text{ ms}$.
- **Error Budget**: Permite hasta un $5\%$ de las peticiones excediendo el percentil esperado.

---

### 2.3 ETL Success Rate

- **Definición**: Proporción de ejecuciones de pipelines de extracción, normalización y carga que concluyen con estado `success` frente al total de ejecuciones programadas y manuales.
- **Métrica Prometheus**: `etl_runs_total`
- **Fórmula SLI (PromQL ventana 24h)**:
  ```promql
  sum(rate(etl_runs_total{status="success"}[24h]))
  /
  sum(rate(etl_runs_total[24h]))
  ```
- **Recording Rule**: `sli:etl_success:ratio_rate24h`
- **Objetivo**: $\ge 98.0\%$ de ejecuciones exitosas.
- **Error Budget**: Se toleran fallas transitorias aisladas (máximo $2\%$ en 30 días) siempre que los reintentos automáticos resuelvan la ingesta.

---

### 2.4 Data Freshness SLO

- **Definición**: Porcentaje del tiempo operacional en que el dataset de licitaciones y órdenes de compra se mantiene con una antigüedad inferior o igual a 24 horas ($\le 86,400\text{ s}$).
- **Comportamiento Fuente**: ChileCompra actualiza publicaciones en días hábiles (lunes a viernes de 08:00 a 19:00 CLT). En fines de semana, los datos pueden tener una antigüedad de 18 a 36 horas sin que constituya una falla del sistema.
- **Métrica Prometheus**: `data_freshness_seconds` (Gauge)
- **Fórmula SLI (PromQL ventana 24h)**:
  ```promql
  avg_over_time((data_freshness_seconds <= bool 86400)[24h:1m])
  ```
- **Recording Rule**: `sli:data_freshness_slo:ratio_rate24h`
- **Objetivo**: $\ge 95.0\%$ del tiempo dentro del umbral de frescura de 24 horas.

---

## 3. Política de Alertas por Consumo de Presupuesto de Error (Burn Rates)

Siguiendo las mejores prácticas del **Google SRE Book**, se implementan alertas multi-ventana basadas en la tasa de consumo (*Burn Rate*):

| Nivel de Alerta | Ventana Corta | Ventana Larga | Tasa de Quemado (*Burn Rate*) | Consumo de Presupuesto | Acción Requerida |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Crítica (Page)** | 5 minutos | 1 hora | $14.4\times$ | $2.0\%$ en 1 hora | Intervención inmediata; riesgo inminente de incumplimiento de SLO. |
| **Advertencia (Ticket)** | 30 minutos | 6 horas | $6.0\times$ | $5.0\%$ en 6 horas | Triage prioritario durante la jornada laboral. |
| **Informativa (Slack)** | 2 horas | 24 horas | $1.0\times$ | $10.0\%$ en 24 horas | Revisión en reunión semanal de confiabilidad. |

---

## 4. Visualización y Reglas de Registro

- **Reglas de Prometheus**: Definidas en `docker/monitoring/prometheus/rules/slo.yml` e `infrastructure/monitoring/prometheus/rules/slo.yml`.
- **Dashboard de Grafana**: Dashboard dedicado `slo-monitoring.json` ubicado en `docker/monitoring/grafana/dashboards/` e `infrastructure/monitoring/grafana/dashboards/`.
