# ADR-011: Adopción de la Pila Prometheus, Grafana, Loki y Sentry para Observabilidad

- **Status**: Aceptado
- **Fecha**: 2026-09-18
- **Decisores**: Equipo de Infraestructura y Confiabilidad (SRE)

---

## Contexto
MercadoInsight integra múltiples capas: frontend, backend, workers asíncronos, bases de datos y llamadas a LLMs. Es imprescindible contar con observabilidad integral basada en los tres pilares: métricas, logs y trazas/errores, permitiendo monitorear SLOs y detectar degradaciones operacionales de inmediato.

## Decisión
Desplegar una arquitectura de observabilidad unificada basada en:
- **Prometheus**: Recolección de métricas numéricas y evaluación de alertas.
- **Grafana**: Visualización en 8 dashboards operacionales dedicados.
- **Loki & Promtail**: Agregación e indexación de logs JSON estructurados.
- **Alertmanager**: Despacho y enrutamiento de notificaciones críticas.
- **Sentry**: Rastreo de excepciones en tiempo real en frontend y backend con release tracking.

## Alternativas Consideradas
1. **Datadog / New Relic**: Plataformas SaaS extremadamente potentes, pero con costes mensuales elevados y basados en volumen que crecen drásticamente con millones de logs de ETL.
2. **Elasticsearch / Logstash / Kibana (ELK Stack)**: Solución clásica de logging, pero consume significativamente más recursos de CPU y RAM que la combinación ligera de Prometheus + Loki.

## Consecuencias
- **Positivas**:
  - Pila 100% de código abierto y autoalojada, con predecibilidad total de costes de infraestructura.
  - Integración nativa entre Grafana, Prometheus y Loki: es posible saltar desde una alerta métrica directamente al log contextual correspondiente usando `request_id`.
  - Captura automatizada de métricas de negocio personalizadas (`market_insight_*`).
- **Negativas**:
  - Requiere administrar el ciclo de vida y retención de las series temporales en el almacenamiento del contenedor de Prometheus y Loki.
