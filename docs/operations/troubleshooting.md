# Manual de Resolución de Incidentes — Troubleshooting Runbooks

Este documento contiene los manuales de procedimiento operacional (*Runbooks*) para el diagnóstico y resolución paso a paso de los tres incidentes más críticos y frecuentes en **MercadoInsight**.

---

## 1. Runbook: API Caída (API Outage / 502 Bad Gateway)

### 1.1 Diagrama de Diagnóstico Rápido
```text
¿Responde https://mercadoinsight.cl/health/ready?
  ├── Sí (200 OK) ──> Revisar latencia en Grafana / NGINX rate limiting
  └── No / Timeout / 502
        │
        ▼
¿Están corriendo los contenedores? (docker ps)
  ├── Backend detenido ──> Inspeccionar logs (docker logs backend) y reiniciar
  └── Backend corriendo
        │
        ▼
¿PostgreSQL responde? (docker exec postgres pg_isready)
  ├── No ──> Ver sección 1.4 (PostgreSQL unresponsive)
  └── Sí
        │
        ▼
¿Redis responde? (docker exec redis redis-cli ping)
  ├── No ──> Reiniciar Redis
  └── Sí ──> Saturación de conexiones o Deadlock en Uvicorn
```

### 1.2 Procedimiento Paso a Paso

1. **Revisar Grafana**:
   - Abrir tablero `SLO Monitoring` (`http://localhost:3000/d/slo-monitoring`).
   - Identificar cuándo comenzó la degradación y si se correlaciona con un pico de tráfico o despliegue reciente.
2. **Revisar Logs en Loki**:
   - Abrir `Logs Explorer` en Grafana o consultar via Docker:
     ```bash
     docker logs --tail 200 -f market_insight_backend
     ```
   - Filtrar por `ERROR` o `CRITICAL`. Buscar `OperationalError` de base de datos o excepciones no capturadas.
3. **Revisar Endpoint de Salud**:
   ```bash
   curl -i http://localhost:8000/health/ready
   ```
   Analizar el JSON retornado. Identificar cuál dependencia específica (`database`, `redis`, `minio`) falló.
4. **Revisar PostgreSQL**:
   ```bash
   docker exec -it market_insight_postgres pg_isready -U postgres
   # Comprobar conexiones activas
   docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   "
   ```
5. **Revisar Redis**:
   ```bash
   docker exec -it market_insight_redis redis-cli ping
   docker exec -it market_insight_redis redis-cli info memory
   ```
6. **Revisar Contenedores Docker**:
   ```bash
   docker ps --filter "name=market_insight"
   ```
7. **Reinicio Seguro (Únicamente si Corresponde)**:
   - **Nunca reiniciar la base de datos de forma abrupta si está ejecutando checkpoints.**
   - Si el backend está bloqueado por saturación de workers Uvicorn:
     ```bash
     docker compose -f docker/compose/docker-compose.prod.yml restart backend
     ```
8. **Registrar Incidente**:
   - Registrar la falla en el canal de incidentes y abrir ticket en Jira/GitHub con el identificador del incidente.

---

## 2. Runbook: Pipeline ETL Detenido o Fallido

### 2.1 Síntomas
- Se dispara la alerta Prometheus `ETLDelayWarning` o `ETLPipelineFailed`.
- El dashboard `Data Quality Monitoring` muestra desfase mayor a 12 horas en compras públicas.

### 2.2 Procedimiento Paso a Paso

1. **Revisar Última Ejecución**:
   ```bash
   docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "
   SELECT run_id, source, records_received, records_valid, records_quarantined, status, duration_seconds, started_at
   FROM core.etl_runs ORDER BY started_at DESC LIMIT 5;
   "
   ```
2. **Revisar Error Específico en Logs**:
   ```bash
   docker logs --tail 300 market_insight_celery_worker | grep -i "etl"
   ```
3. **Revisar Conectividad con la API de ChileCompra**:
   - Comprobar si la API oficial está respondiendo o arrojando códigos `503 Service Unavailable` / `429 Too Many Requests`:
     ```bash
     curl -i "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?fecha=20260922&ticket=$CHILECOMPRA_TICKET"
     ```
   - Si la API externa está caída, verificar si el incidente es general en `mercadopublico.cl`.
4. **Revisar Registros Procesados vs. Cuarentena**:
   - Inspeccionar la tabla de cuarentena para verificar si hubo un cambio de esquema no retrocompatible en la fuente externa:
     ```bash
     docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "
     SELECT error_reason, count(*) FROM core.quarantine_records 
     WHERE created_at > now() - interval '24 hours' GROUP BY error_reason;
     "
     ```
5. **Reejecutar Pipeline desde Checkpoint**:
   - Lanzar la corrida manual respetando el último checkpoint registrado:
     ```bash
     docker compose -f docker/compose/docker-compose.prod.yml run --rm backend python -m app.etl.pipeline --resume-from-checkpoint
     ```
6. **Validar Integridad**:
   - Confirmar que el nuevo registro en `core.etl_runs` tenga `status = 'SUCCESS'`.
   - Verificar la actualización de la métrica `market_insight_data_freshness_seconds`.

---

## 3. Runbook: Almacenamiento PostgreSQL Lleno (Disk Space Full)

### 3.1 Síntomas
- Alerta Prometheus `DatabaseDiskSpaceFilling` o logs de PostgreSQL con `FATAL: could not write to file ... No space left on device`.
- PostgreSQL entra en modo de solo lectura para evitar corrupción catastrófica.

### 3.2 Procedimiento Paso a Paso

1. **Revisar Tamaño de la Base de Datos**:
   ```bash
   docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "
   SELECT pg_size_pretty(pg_database_size('market_insight')) AS db_size;
   "
   ```
2. **Revisar Tablas e Índices Más Pesados**:
   ```bash
   docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "
   SELECT schemaname || '.' || relname AS table,
          pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
          pg_size_pretty(pg_relation_size(relid)) AS data_size,
          pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
   FROM pg_catalog.pg_statio_user_tables
   ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
   "
   ```
3. **Revisar Logs del Sistema y de Contenedores**:
   - Comprobar si los logs de Docker están consumiendo espacio excesivo:
     ```bash
     df -h
     du -sh /var/lib/docker/containers/*
     ```
   - Si los logs están llenando el disco, truncar logs antiguos:
     ```bash
     truncate -s 0 /var/lib/docker/containers/*/*-json.log
     ```
4. **Revisar Directorio WAL (*Write-Ahead Logging*)**:
   - Comprobar si hay acumulación de archivos WAL no archivados en `/var/lib/postgresql/data/pg_wal`.
   - Verificar que el script de archivado de WAL hacia MinIO o backup secundario no esté trabado.
5. **Revisar Respaldos Antiguos**:
   - Comprobar si respaldos locales obsoletos no fueron podados por la política de retención:
     ```bash
     ls -lh /var/backups/market-insight/
     # Limpiar respaldos con más de 14 días manualmente si es necesario
     find /var/backups/market-insight/ -name "backup_*.dump" -mtime +14 -delete
     ```
6. **Liberar o Expandir Almacenamiento**:
   - **Vaciar Tablas Temporales o Cuarentena Histórica Resuelta**:
     ```sql
     DELETE FROM core.quarantine_records WHERE created_at < now() - interval '60 days' AND resolved = true;
     VACUUM FULL core.quarantine_records;
     ```
   - **Expandir Volumen LVM / Cloud Disk**: Si el crecimiento es genuino por volumen histórico de compras públicas, redimensionar el disco del servidor (`lvextend -r`).
7. **Verificar Recuperación**:
   - Comprobar que el espacio libre en disco supere al menos el 20%:
     ```bash
     df -h /var/lib/docker
     ```
   - Validar que PostgreSQL acepte escrituras:
     ```bash
     docker exec -it market_insight_postgres psql -U postgres -d market_insight -c "SELECT txid_current();"
     ```

---

## 4. Procedimientos de Escalamiento

Para cualquiera de los incidentes descritos, si la mitigación no se logra en los primeros 15 minutos:
1. Notificar al canal `#incident-war-room`.
2. Seguir la matriz RACI y protocolo de [incidents.md](incidents.md).
3. Si existe riesgo inminente de corrupción de datos, activar inmediatamente el modo de mantenimiento en NGINX.
