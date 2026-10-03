# Estrategia de Backups — MercadoInsight

Este documento define la arquitectura, políticas de retención, automatización y validación de respaldos para los datos y configuraciones críticas de **MercadoInsight**, cumpliendo con la subfase **10.14 (Backup)** de la Fase 10.

---

## 1. Objetivos y Alcance del Respaldo

La estrategia garantiza la disponibilidad e integridad de los datos ante fallas de hardware, corrupción lógica o incidentes operacionales, protegiendo:

1. **Base de Datos PostgreSQL**: Esquemas relacionales `public`, `staging`, `dw`, `knowledge` y vectores en `pgvector`.
2. **Almacenamiento de Objetos (MinIO)**: Buckets con documentos JSON brutos de licitaciones, bases técnicas PDF y modelos serializados.
3. **Configuraciones Críticas**: Plantillas de variables de entorno cifradas, configuraciones perimetrales NGINX y reglas de alerta en Prometheus.
4. **Metadatos de Recuperación**: Manifiestos criptográficos inmutables (`manifest.json`) con hashes SHA-256 y marcas temporales.

---

## 2. Frecuencias y Política de Retención

La frecuencia responde al objetivo de punto de recuperación (**RPO <= 24h** para respaldos completos y **RPO <= 1h** con WAL archiving):

| Nivel | Frecuencia | Hora de Ejecución | Política de Retención | Destino / Almacenamiento |
| :--- | :--- | :--- | :--- | :--- |
| **Diario (Daily)** | Cada 24 horas | 02:00 UTC | **14 días** | Disco local dedicado + Almacenamiento secundario |
| **Semanal (Weekly)** | Cada Domingo | 03:00 UTC | **4 semanas** | Almacenamiento secundario externo (Object Storage S3/GCS) |
| **Mensual (Monthly)**| 1º de cada mes | 04:00 UTC | **12 meses** | Almacenamiento inmutable en frío (Cold Archive / Glacier) |

---

## 3. Formato y Tecnologías de Respaldo

### 3.1 PostgreSQL: `pg_dump -Fc`
Se utiliza el formato binario custom comprimido (`-Fc`):
* **Ventajas**: Compresión integrada con zlib (nivel 9), inclusión de blobs y metadatos, y capacidad de restauración selectiva o paralela (`pg_restore -j 4`).
* **Comando base**:
  ```bash
  pg_dump --dbname "$DATABASE_URL" --format=c --compress=9 --blobs --file "$BACKUP_FILE"
  ```

### 3.2 WAL Archiving y PITR (Point-in-Time Recovery)
Para entornos de alta criticidad, PostgreSQL se configura con archivado continuo de Write-Ahead Logging (WAL):
* En `postgresql.conf`:
  ```ini
  wal_level = replica
  archive_mode = on
  archive_command = 'test ! -f /mnt/wal_archive/%f && cp %p /mnt/wal_archive/%f'
  archive_timeout = 3600
  ```
* Permite reconstruir el estado de la base de datos hasta cualquier segundo específico antes de una contingencia.

### 3.3 MinIO / Object Storage
Sincronización de buckets mediante `mc mirror`:
```bash
mc mirror --overwrite --remove local/market-insight-raw backup-target/market-insight-raw
```

---

## 4. Script de Automatización: `backup.py`

Se dispone del script oficial [`infrastructure/scripts/backup.py`](file:///c:/Users/artut/market-insight/infrastructure/scripts/backup.py) para orquestar la ejecución desatendida de respaldos:

```bash
# Ejecución de respaldo completo
python infrastructure/scripts/backup.py --type full --retention-days 14

# Respaldo exclusivo de base de datos
python infrastructure/scripts/backup.py --type postgres --output-dir /var/backups/mercadoinsight

# Modo simulación (Dry-Run)
python infrastructure/scripts/backup.py --dry-run
```

### Estructura del Manifiesto Criptográfico (`manifest.json`)
Cada corrida de respaldo genera un manifiesto inmutable con la información necesaria para auditoría y validación previa a la restauración:

```json
{
  "backup_id": "backup_20260922_020000Z",
  "timestamp_utc": "2026-09-22T02:00:00.123456Z",
  "backup_type": "full",
  "status": "SUCCESS",
  "app_version": "1.0.0",
  "files": [
    {
      "target": "postgres",
      "filename": "postgres_backup_20260922_020000Z.dump",
      "size_bytes": 145829120,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      "target": "config",
      "filename": "config_backup_20260922_020000Z.tar.gz",
      "size_bytes": 128450,
      "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
    }
  ],
  "pruned_files": [
    "postgres_backup_20260907_020000Z.dump"
  ],
  "retention_days": 14,
  "dry_run": false
}
```

---

## 5. Monitoreo y Alertas

1. **Detección de Fallos**: El script retorna código de salida `0` ante éxito y `1` ante error, registrando el incidente en los logs estructurados.
2. **Alerta en Prometheus**: Las métricas de backup reportan el timestamp del último respaldo exitoso (`last_successful_backup_timestamp_seconds`).
3. **Regla de Alerta**:
   ```yaml
   - alert: BackupStaleOrFailed
     expr: time() - last_successful_backup_timestamp_seconds > 90000
     for: 15m
     labels:
       severity: critical
     annotations:
       summary: "Respaldo diario de MercadoInsight no ejecutado o fallido hace más de 25 horas"
   ```
