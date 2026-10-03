# Guía de Recuperación ante Desastres — Disaster Recovery

Este documento complementa el runbook maestro [DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md), formalizando los procedimientos técnicos, las herramientas y la validación periódica para la continuidad operativa de **MercadoInsight**.

---

## 1. Métricas Clave de Recuperación

| Métrica | Objetivo Comprometido | Mecanismo de Garantía |
| :--- | :--- | :--- |
| **RPO** (*Recovery Point Objective*) | **$\le 1$ hora** (con WAL) / **$\le 24$ horas** (con dumps) | Respaldos diarios `pg_dump -Fc` a las 02:00 UTC y archivado continuo de WALs hacia MinIO/S3. |
| **RTO** (*Recovery Time Objective*) | **$\le 1$ hora** | Script automatizado `restore.py` con comprobación SHA-256 previa a la restauración y aprovisionamiento Docker. |

---

## 2. Herramientas Operacionales

### 2.1 Generación de Backups (`backup.py`)
```bash
python infrastructure/scripts/backup.py --type full --output-dir /var/backups/market-insight --retention-days 14
```
- Genera dump binario de PostgreSQL (`.dump`), archivo de MinIO (`.tar.gz`) y configuración cifrada.
- Crea un manifiesto inmutable `manifest.json` con hash SHA-256 individual por archivo.

### 2.2 Restauración Segura (`restore.py`)
```bash
# Modo verificación (sin alterar la base de datos viva)
python infrastructure/scripts/restore.py --manifest /var/backups/market-insight/manifest_latest.json --verify-only

# Restauración en producción o ambiente de recuperación
python infrastructure/scripts/restore.py --manifest /var/backups/market-insight/manifest_latest.json
```
- **Detección de Manipulación**: Cancela de inmediato si cualquier hash SHA-256 no coincide exactamente con el manifiesto.
- **Validación Post-Restauración**: Verifica tablas maestras de `core`, `analytics` y versión de Alembic.

---

## 3. Escenarios de Desastre Contemplados

1. **Corrupción de Base de Datos PostgreSQL**:
   - Recreación del cluster y restauración limpia vía `pg_restore`.
2. **Pérdida de Almacenamiento MinIO**:
   - Restauración de buckets (`tenders-docs`, `backups`) desde archivo `.tar.gz`.
3. **Pérdida Total del Servidor / Host**:
   - Reconstrucción sobre nuevo servidor Ubuntu 24.04 mediante `docker-compose.prod.yml` y restauración desde backup remoto.
4. **Compromiso de Credenciales o Secretos**:
   - Rotación inmediata de `SECRET_KEY`, credenciales de base de datos y llaves de LLM, invalidando tokens JWT previos.

---

## 4. Simulacros Periódicos (DR Drills)

- Frecuencia: **Semestral**.
- Entorno: **Recovery Sandbox** aislado de producción.
- Aprobación: El simulacro se considera exitoso si la restauración completa y verificación de endpoints toma menos de 45 minutos.
