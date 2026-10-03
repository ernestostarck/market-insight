# Manual de Operaciones — Backups & Retención

Este documento establece los procedimientos rutinarios y de emergencia para la ejecución, validación y gestión del ciclo de vida de los respaldos de **MercadoInsight**.

---

## 1. Política de Respaldo

| Nivel | Frecuencia | Retención | Contenido |
| :--- | :--- | :--- | :--- |
| **Diario** | Todos los días a las 02:00 UTC | 14 días | Dump binario comprimido de PostgreSQL (`pg_dump -Fc`), esquemas `core`, `analytics`, `knowledge`, `dw`, `marts` y archivos de MinIO. |
| **Semanal** | Domingos a las 03:00 UTC | 4 semanas | Snapshot completo acumulativo con verificación de integridad de índices HNSW. |
| **Mensual** | Primer día de cada mes | 12 meses | Respaldo archivado inmutable en almacenamiento externo secundario (S3 / Cold Storage). |

---

## 2. Ejecución de Backups

### 2.1 Respaldo Completo Manual
```bash
python infrastructure/scripts/backup.py --type full --output-dir /var/backups/market-insight --retention-days 14
```

### 2.2 Respaldo Exclusivo de Base de Datos
```bash
python infrastructure/scripts/backup.py --type postgres --output-dir /var/backups/market-insight
```

### 2.3 Modo Dry-Run (Verificación sin escribir)
```bash
python infrastructure/scripts/backup.py --type full --output-dir /var/backups/market-insight --dry-run
```

---

## 3. Manifiesto y Checksum SHA-256

Cada ejecución de `backup.py` genera:
- `backup_postgres_<timestamp>.dump`
- `backup_minio_<timestamp>.tar.gz`
- `backup_config_<timestamp>.tar.gz`
- `manifest_<timestamp>.json` y `manifest.json` (puntero al último respaldo)

Estructura del manifiesto:
```json
{
  "timestamp": "2026-09-22T02:00:00Z",
  "backup_type": "full",
  "app_version": "1.0.0",
  "files": {
    "postgres": {
      "filename": "backup_postgres_20260922_020000.dump",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size_bytes": 104857600
    }
  }
}
```

---

## 4. Política de Poda y Limpieza (Retention Pruning)

El script `backup.py` ejecuta automáticamente la eliminación de respaldos que excedan los días de retención (`--retention-days`):
- Los respaldos diarios de más de 14 días son eliminados localmente.
- Si un backup es semanal (domingo) o mensual (día 1), se preserva según la política correspondiente.
- Se mantiene siempre al menos **el último respaldo exitoso**, independientemente de su antigüedad.

---

## 5. Verificación de Integridad de Respaldos

Para comprobar que los respaldos no han sido alterados ni corrompidos en disco:
```bash
python infrastructure/scripts/restore.py --manifest /var/backups/market-insight/manifest.json --verify-only
```
Si los hashes coinciden, devolverá `Checksum verification: SUCCESS`. Si un solo archivo fue modificado, el proceso fallará con error crítico `TAMPER_DETECTED`.
