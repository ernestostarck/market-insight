# Pipeline ETL — Ingesta y Transformación de Datos

Este documento describe la arquitectura técnica, las fases y los mecanismos de resiliencia del pipeline de Extracción, Transformación y Carga (ETL) de **MercadoInsight**.

---

## 1. Etapas del Pipeline

```text
               ┌───────────────────────┐
               │ ChileCompra API v1/v2 │
               └───────────┬───────────┘
                           │ 1. Extracción (HTTP / Bulk)
                           ▼
               ┌───────────────────────┐
               │    Raw JSONB Store    │ (Trazabilidad y replay inmutable)
               └───────────┬───────────┘
                           │ 2. Validación Pydantic
                           ▼
                 ¿Esquema Válido?
                 ├── No ──> [ Quarantine Queue ] ──> Alerta de calidad
                 └── Sí
                           │ 3. Normalización y Limpieza
                           ▼
               ┌───────────────────────┐
               │     Normalización     │ (Fechas UTC, RUTs con DV, tipos numéricos)
               └───────────┬───────────┘
                           │ 4. Deduplicación
                           ▼
               ┌───────────────────────┐
               │  Deduplication Check  │ (Hash SHA-256 + Códigos naturales)
               └───────────┬───────────┘
                           │ 5. Carga Optimizada
                           ▼
               ┌───────────────────────┐
               │   PostgreSQL COPY     │ (Transaccional en esquema `core`)
               └───────────┬───────────┘
                           │ 6. Disparo de Enriquecimiento
                           ▼
               [ Cola Celery: nlp_tasks ]
```

---

## 2. Ingesta Incremental y Checkpoints

Para evitar consultas redundantes y mitigar rate limits de ChileCompra:
1. **Puntos de Control (Checkpoints)**:
   - Se registra en la tabla `etl_runs` el último timestamp procesado exitosamente por cada tipo de recurso (`licitaciones`, `ordenes_compra`).
2. **Ventana de Solapamiento**:
   - Cada ejecución incremental consulta desde `last_checkpoint - 3 horas` para absorber licitaciones que hayan sido modificadas retroactivamente en la plataforma pública.
3. **Idempotencia**:
   - El uso de `ON CONFLICT (codigo_externo) DO UPDATE` garantiza que reejecutar una ventana de tiempo no duplique registros.

---

## 3. Manejo de Cuarentena (Quarantine)

Cuando un registro de ChileCompra presenta malformaciones graves (fechas futuras incoherentes, montos negativos, caracteres no UTF-8):
- **Aislamiento**: El registro se persiste íntegramente en la tabla `quarantine_records` en formato JSONB original junto con el mensaje de error de validación.
- **No Interrupción**: Un registro defectuoso **nunca detiene el procesamiento del lote completo**.
- **Auditoría**: Los registros en cuarentena son expuestos en Grafana (`data-quality-monitoring.json`) para revisión y triage de anomalías.

---

## 4. Métricas y Auditoría por Corrida

Cada lote ejecutado genera un registro en `etl_runs` con:
- `run_id`: UUID único.
- `source`: API oficial vs. Datos abiertos (bulk).
- `records_received`, `records_valid`, `records_quarantined`, `records_inserted`, `records_updated`.
- `duration_seconds`: Tiempo de ejecución.
- `status`: `SUCCESS`, `PARTIAL_SUCCESS` o `FAILED`.
