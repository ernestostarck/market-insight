# Procedimiento de Rollback de Emergencia

Este documento establece el protocolo formal de **reversión (rollback)** ante despliegues fallidos o incidencias críticas detectadas tras una actualización en Staging o Producción.

---

## 1. Criterios para Activar Rollback

Se debe iniciar el procedimiento de reversión si tras el despliegue:
1. El endpoint `/health/ready` falla de forma persistente por más de 3 minutos.
2. La tasa de errores HTTP 5xx excede el 1% en los primeros 10 minutos (alerta `APIErrorRateHigh`).
3. Se detecta corrupción o incompatibilidad irreversible en las consultas de base de datos.
4. Las pruebas de humo post-despliegue fallan en funcionalidades centrales (búsqueda de licitaciones o login).

---

## 2. Procedimiento de Rollback Rápido (Contenedores)

Si el fallo se debe a un bug de código en el backend, frontend o worker (sin cambios destructivos de esquema en base de datos):

1. **Revertir Imágenes a la Versión Anterior**:
   ```bash
   cd /opt/market-insight
   
   # Ejemplo: Revertir de v1.0.1 a v1.0.0
   export PREVIOUS_TAG=v1.0.0
   
   docker compose -f docker/compose/docker-compose.prod.yml pull
   TAG=$PREVIOUS_TAG docker compose -f docker/compose/docker-compose.prod.yml up -d --no-deps backend frontend celery_worker
   ```

2. **Verificar Recuperación**:
   ```bash
   curl -f https://mercadoinsight.cl/health/ready
   ```

---

## 3. Rollback de Migraciones de Base de Datos (Alembic)

Si el despliegue incluyó una migración de base de datos que introdujo errores:

1. **Identificar la Revisión Destino**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend alembic current
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend alembic history --verbose -n 3
   ```

2. **Ejecutar el Downgrade**:
   ```bash
   # Retroceder una revisión
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend alembic downgrade -1
   
   # O retroceder a un hash específico
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend alembic downgrade 20260920_0017
   ```

3. **Revisar Consistencia de Datos**:
   ```bash
   docker compose -f docker/compose/docker-compose.prod.yml run --rm backend python -c "
   from app.db.session import engine
   from sqlalchemy import text
   with engine.connect() as conn:
       res = conn.execute(text('SELECT version_num FROM alembic_version')).scalar()
       print(f'Alembic current version: {res}')
   "
   ```

---

## 4. Rollback Catastrófico (Restauración de Backup)

En caso de corrupción de datos o fallo de migración no recuperable mediante downgrade:
1. Activar el runbook de Disaster Recovery detallado en [DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md).
2. Ejecutar restauración completa desde el último backup verificado:
   ```bash
   python infrastructure/scripts/restore.py --manifest /var/backups/market-insight/manifest_latest.json
   ```

---

## 5. Comunicación y Post-Mortem

- Notificar de inmediato al canal de incidentes (`#incidents-alerts`).
- Registrar la reversión en el tablero de estado operacional.
- Convocar sesión de post-mortem sin culpas dentro de las siguientes 24 horas.
