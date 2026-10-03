# Monitoreo de Costos y Gobernanza de IA — MercadoInsight

Este documento detalla el sistema de auditoría, registro granular, detección de anomalías y control presupuestario para la inferencia de modelos de lenguaje (LLM) y pipelines RAG en **MercadoInsight** (Fase 10.18).

---

## 1. Justificación y Objetivos

Con la integración de asistentes conversacionales generativos y búsqueda semántica (Fase 9), el consumo de tokens deja de ser una métrica puramente técnica y se convierte en un **costo operacional directo**. El sistema de monitoreo asegura:

* **Trazabilidad Total**: Cada interacción registra el número exacto de tokens de entrada (prompt + contexto), tokens de salida (respuesta generada) y costo estimado en USD.
* **Atribución Granular**: Capacidad de atribuir costos por consulta, conversación, usuario autenticado, modelo (`gemini-2.5-flash`, `gemini-1.5-pro`, `gpt-4o-mini`), intención y proveedor.
* **Detección Temprana de Anomalías**: Identificación proactiva de bucles de reintento, prompts inflados y consultas que superan los umbrales de presupuesto.
* **Protección Presupuestaria**: Alertas automáticas en Prometheus y Alertmanager ante desviaciones del gasto proyectado.

---

## 2. Catálogo de Precios por Modelo

El módulo [`apps/backend/app/ai/cost_tracker.py`](file:///c:/Users/artut/market-insight/apps/backend/app/ai/cost_tracker.py) define el tarifario canonical de inferencia (USD por cada 1,000,000 de tokens):

| Modelo | Proveedor | Entrada (USD / 1M tokens) | Salida (USD / 1M tokens) | Caso de Uso en MercadoInsight |
| :--- | :--- | :--- | :--- | :--- |
| **`gemini-2.5-flash`** | Google | **$0.075** | **$0.30** | Motor conversacional y síntesis principal (Default). |
| **`gemini-1.5-flash`** | Google | **$0.075** | **$0.30** | Extracción estructurada y clasificación de entidades. |
| **`gemini-1.5-pro`** | Google | **$1.250** | **$5.00** | Consultas complejas de análisis multi-documento. |
| **`gpt-4o-mini`** | OpenAI | **$0.150** | **$0.60** | Motor secundario de fallback y contrastación. |
| **`local-deterministic`** | Local | **$0.000** | **$0.00** | Respuestas basadas en reglas simbólicas y plantillas SQL. |

---

## 3. Registro y Atribución por Consulta

Cada ejecución de inferencia en el backend genera un objeto inmutable `QueryCostRecord`:

```python
class QueryCostRecord(BaseModel):
    query_id: str
    model: str
    provider: str
    intent: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    is_anomalous: bool = False
```

### Agregaciones Disponibles en `CostTracker`
* **Por Consulta**: Cálculo exacto mediante fórmula:
  $$\text{Costo} = \left(\text{tokens\_in} \times \frac{\text{precio\_in}}{10^6}\right) + \left(\text{tokens\_out} \times \frac{\text{precio\_out}}{10^6}\right)$$
* **Por Conversación**: Suma acumulada de costos para todos los turnos de la sesión en PostgreSQL.
* **Por Usuario**: Atribución al UUID del usuario autenticado para análisis de consumo por organización.
* **Diario y Mensual**: Agregación temporal para control presupuestario y conciliación de facturas con proveedores de API.

---

## 4. Detección de Anomalías y Límites de Seguridad

Para prevenir facturaciones imprevistas por ataques de denegación de servicio o consultas malintencionadas:

1. **Límite de Tokens por Consulta**: Configurado en `8,000 tokens`. Consultas que intenten exceder este límite son truncadas por el `ContextBuilder`.
2. **Límite de Costo por Consulta**: Si una única consulta supera los **$0.05 USD**, se marca como `is_anomalous = True` e incrementa el contador de Prometheus `ai_costly_queries_total`.
3. **Guardrails de Inyección**: Intentos de prompt injection o desbordamiento de contexto son bloqueados antes de llamar al proveedor del LLM, incurriendo en costo cero.

---

## 5. Reglas de Alerta en Prometheus

Configuradas en [`docker/monitoring/prometheus/rules/ai-cost.yml`](file:///c:/Users/artut/market-insight/docker/monitoring/prometheus/rules/ai-cost.yml):

* **`AICostSpikeDaily`**: Dispara si el gasto acumulado en 24 horas supera los **$10 USD**.
* **`AIHighTokenConsumptionRate`**: Dispara si la tasa de consumo supera los **1,000 tokens/segundo** durante 5 minutos consecutivos.
* **`AICostlyQueriesSpike`**: Notifica si se registran más de 20 consultas anómalas en una ventana de 1 hora.

---

## 6. Panel de Visualización en Grafana

El dashboard [`rag-monitoring.json`](file:///c:/Users/artut/market-insight/docker/monitoring/grafana/dashboards/rag-monitoring.json) incluye paneles dedicados para:
* Gasto total acumulado en USD (Stat Panel).
* Tasa de consumo de tokens por minuto (Time Series).
* Desglose de gasto por modelo LLM (Pie Chart / Bar Chart).
* Histograma de costo por consulta y registro de anomalías.
