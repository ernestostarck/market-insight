# Definición y Validación de RPO / RTO — MercadoInsight

Este documento establece la derivación técnica, supuestos de infraestructura, procedimientos de prueba y gobernanza para los objetivos de punto y tiempo de recuperación (**RPO / RTO**) de **MercadoInsight** (Fase 10.16).

---

## 1. Justificación Técnica de RPO y RTO

En lugar de definir cifras arbitrarias, los objetivos de recuperación de MercadoInsight se derivan directamente de:
1. **La cadencia de actualización de datos de ChileCompra**: La API pública de Mercado Público publica licitaciones y órdenes de compra de manera continua durante días hábiles, con sincronizaciones batch cada 1 hora.
2. **El Acuerdo de Nivel de Servicio (SLA)**: Compromiso de disponibilidad del **99.5%** en horario hábil (máximo ~3.65 horas de indisponibilidad imprevista al mes).

| Métrica | Objetivo Comprometido | Justificación Técnica | Mecanismo de Garantía |
| :--- | :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | **$\le 1$ hora** (con WAL)<br>**$\le 24$ horas** (respaldo diario) | Las licitaciones del día se pueden reingestar si es necesario desde la API pública, pero el trabajo de etiquetado humano y revisiones de analistas no debe perder más de 1 hora de progreso. | Write-Ahead Logging (WAL) archiving + Respaldo consolidado diario (`pg_dump -Fc`). |
| **RTO (Recovery Time Objective)** | **$\le 1$ hora** (desastre total)<br>**$\le 5$ minutos** (fallo de servicio) | Tiempo necesario para aprovisionar un nuevo nodo Docker, descargar la imagen desde GHCR y restaurar el dump de base de datos verificado con `restore.py`. | Orquestación reproducible en Docker Compose, imágenes preconstruidas en GHCR y scripts de restauración automatizada. |

---

## 2. Relación con la Infraestructura y Estrategia de Backup

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        INFRAESTRUCTURA Y DATOS                         │
│                                                                        │
│   PostgreSQL Base   ──> pg_dump -Fc (Diario a las 02:00 UTC)           │
│   (RPO: <= 24h)                                                        │
│                                                                        │
│   PostgreSQL WAL    ──> Archivador continuo a volumen montado / S3     │
│   (RPO: <= 1h)                                                         │
│                                                                        │
│   Imágenes Docker   ──> Precompiladas en GHCR (RTO: <= 2 min de pull)  │
│                                                                        │
│   Restauración      ──> restore.py (RTO: <= 12 min de pg_restore)      │
│                                                                        │
│   Health Check      ──> /health/ready (RTO: <= 30 seg de probe)        │
└────────────────────────────────────────────────────────────────────────┘
```

### Supuestos de Infraestructura para Cumplir el RTO
1. **Ancho de Banda**: Conexión de red de al menos 100 Mbps para descargar imágenes GHCR (Frontend ~40MB, Backend ~180MB) y el último dump de base de datos (~150MB a 500MB) en menos de 3 minutos.
2. **I/O de Almacenamiento**: Disco SSD / NVMe con rendimiento de escritura $\ge 150 \text{ MB/s}$ para que `pg_restore` reconstruya tablas e índices vectoriales en menos de 15 minutos.
3. **Imágenes Inmutables**: Las imágenes de producción ya están construidas y testeadas en GHCR, eliminando tiempos de compilación durante una contingencia.

---

## 3. Pruebas de Validación de RPO

Para validar que el RPO efectivo cumple con la cota de $\le 1$ hora:
* **Prueba de Checkpoints de Ingestión**: Se verifica que la tabla `etl_runs` y los checkpoints incrementales registren la última fecha/hora de transacción procesada.
* **Prueba de Reingesta Idempotente**: Se simula la pérdida de las últimas 2 horas de datos relacionales y se ejecuta el pipeline ETL incremental; el pipeline debe recuperar los registros faltantes sin generar duplicados gracias a las restricciones `UNIQUE(codigo_externo)`.

---

## 4. Simulación de RTO (Cronometrada)

En los simulacros de recuperación ante desastres (Disaster Recovery Drills):
1. **Inicio de Cronómetro ($T_0$)**: Se simula la caída del host y se inicia el aprovisionamiento de un contenedor aislado `postgres` temporal.
2. **Descarga y Verificación ($T_1$)**: Verificación del hash SHA-256 del manifiesto con `restore.py --verify-only` (~15 segundos).
3. **Restauración de Esquema y Datos ($T_2$)**: Ejecución de `pg_restore` (~8 minutos para 2 millones de filas).
4. **Verificación de Migraciones y Health Probes ($T_3$)**: `alembic current` y comprobación de endpoints `/health/ready` (~45 segundos).
5. **Tiempo Total Observado ($T_{total} = T_3 - T_0$)**: **$\approx 9.5$ minutos**, ampliamente inferior al umbral máximo permitido de **60 minutos** (RTO).

---

## 5. Revisión Periódica y Gobernanza

* **Frecuencia de Revisión**: Cada **3 meses** junto con el simulacro de Disaster Recovery.
* **Criterios de Ajuste**: Si el volumen de la base de datos supera los 50 GB o los índices vectoriales de `pgvector` incrementan el tiempo de `pg_restore` por encima de 30 minutos, se deben implementar réplicas de lectura en caliente (Streaming Replication / Hot Standby) para reducir el RTO a $< 1$ minuto.
