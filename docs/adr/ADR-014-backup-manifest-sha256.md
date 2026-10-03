# ADR-014: Estrategia de Respaldos Criptográficamente Verificados con Manifiesto SHA-256

- **Status**: Aceptado
- **Fecha**: 2026-09-21
- **Decisores**: Equipo de Infraestructura y Continuidad del Negocio

---

## Contexto
En caso de un incidente catastrófico (fallo de hardware, corrupción de base de datos o ataque de ransomware), restaurar a ciegas un archivo de respaldo sin verificar si fue truncado, corrompido por almacenamiento defectuoso o alterado por un atacante puede ocasionar pérdidas de datos irreversibles o inyección de código malicioso.

## Decisión
Implementar un sistema de respaldo y restauración cerrado (`backup.py` y `restore.py`) gobernado por un **manifiesto inmutable en JSON con firmas hash SHA-256 individuales por cada archivo componente**:
- Cada dump de PostgreSQL (`.dump`), archivo de MinIO (`.tar.gz`) y configuración cifrada tiene su hash SHA-256 registrado en `manifest_<timestamp>.json`.
- El script de restauración `restore.py` verifica obligatoriamente los hashes antes de tocar la base de datos viva; si un solo bit no coincide, la operación se cancela de inmediato por alerta de manipulación (*tamper detection*).

## Alternativas Consideradas
1. **Dumps Crudos sin Manifiesto**: Ejecutar `pg_dump` directo a un archivo plano. Es vulnerable a archivos incompletos generados por cortes de energía y no ofrece verificación de integridad antes del restore.
2. **Snapshots de Disco de Nivel de Bloque (Cloud EBS / LVM)**: Muy rápidos, pero no garantizan consistencia transaccional sin congelar la base de datos y no permiten restaurar componentes individuales (como una sola tabla o bucket).

## Consecuencias
- **Positivas**:
  - Garantía matemática de integridad antes de iniciar cualquier procedimiento de recuperación ante desastres.
  - Soporte para modo de verificación sin impacto (`--verify-only`).
  - Alineación estricta con el objetivo de resiliencia: RPO $\le 1$h/24h y RTO $\le 1$h.
- **Negativas**:
  - Requiere unos segundos adicionales durante el proceso de respaldo y restauración para computar los checksums SHA-256.
