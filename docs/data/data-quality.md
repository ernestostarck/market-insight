# Calidad y Gobierno de Datos — Data Quality

Este documento define el marco de aseguramiento de calidad de datos, reglas de validación, frescura y monitoreo de anomalías en **MercadoInsight**.

---

## 1. Dimensiones de Calidad de Datos

| Dimensión | Definición | Regla en MercadoInsight |
| :--- | :--- | :--- |
| **Completitud** | Proporción de atributos requeridos presentes | Códigos de licitación, RUTs de organismos y montos no pueden ser nulos en el esquema canónico. |
| **Consistencia** | Coherencia entre entidades relacionadas | Toda oferta adjudicada debe pertenecer a una licitación existente en `core.licitaciones`. |
| **Validez** | Conformidad con formatos y rangos válidos | Los RUTs deben cumplir algoritmo Módulo 11 con dígito verificador válido. Fechas deben ser cronológicamente posibles. |
| **Unicidad** | Ausencia de registros duplicados | Unicidad estricta por `codigo_externo` en licitaciones y `(licitacion_id, proveedor_id)` en ofertas. |
| **Frescura** | Intervalo entre la publicación oficial y la disponibilidad | Retraso menor a 6 horas para licitaciones activas y menor a 24 horas para adjudicaciones históricas. |

---

## 2. Reglas de Validación Canónica

Implementadas mediante esquemas Pydantic v2 en `app/etl/validation/`:

1. **Validación de RUT**:
   - Limpieza de puntos y guiones.
   - Cálculo de dígito verificador (0-9, K).
   - Rechazo de RUTs de prueba (ej. `1-9`, `12345678-9`).
2. **Validación de Montos Monetarios**:
   - Montos en CLP, USD, UTM o UF normalizados a CLP para comparativas cuantitativas.
   - Montos negativos o superiores a límites absurdos (> 100 mil millones de CLP sin respaldo de gran obra) son marcados para revisión.
3. **Validación Cronológica**:
   - `fecha_publicacion <= fecha_cierre <= fecha_adjudicacion`.

---

## 3. Monitoreo de Frescura y Anomalías

En Prometheus y Grafana:
- **`market_insight_data_freshness_seconds`**: Segundos transcurridos desde la última licitación recibida. Alerta `DataFreshnessLagWarning` si supera las 12 horas en días hábiles.
- **`market_insight_quarantine_records_total`**: Contador de registros desviados a cuarentena. Alerta `QuarantineRateHigh` si la tasa supera el 5% de un lote.
- **Análisis de Dispersión**: Alertas estadísticas automáticas ante caídas abruptas en el volumen diario de compras públicas reportadas por la fuente externa.
