# Guía de Entorno de Staging — Pre-Producción

El entorno de **Staging** es un ambiente idéntico en arquitectura, dependencias y configuración a Producción, utilizado para validaciones finales de regresión, pruebas de carga y verificación de despliegue antes de promover cambios a producción.

---

## 1. Características del Entorno

- **Paridad Arquitectónica**: Opera con la misma separación de red (`public-net` y `private-net`) y los mismos contenedores Docker que Producción.
- **Aislamiento de Datos**: Utiliza un conjunto de datos anonimizado o representativo (Gold Dataset y muestras históricas), **nunca datos productivos con información sensible no ofuscada**.
- **Secretos Aislados**: Claves JWT, contraseñas de bases de datos y tokens de API independientes de Producción.
- **Subredes Dedicadas**: Subred pública `172.29.0.0/16` y subred privada `172.29.1.0/24`.

---

## 2. Despliegue en Staging

### 2.1 Variables de Entorno
Configurar `.env.staging` a partir de `.env.staging.example`:
```ini
ENVIRONMENT=staging
DEBUG=False
SECRET_KEY=<staging_secret_key_random_64_hex>
APP_VERSION=1.0.0
POSTGRES_USER=postgres_staging
POSTGRES_PASSWORD=<staging_secure_pg_password>
POSTGRES_DB=market_insight_staging
DATABASE_URL=postgresql+asyncpg://postgres_staging:<password>@postgres:5432/market_insight_staging
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=staging_minio_access
MINIO_SECRET_KEY=<staging_minio_secret>
CORS_ORIGINS=["https://staging.mercadoinsight.cl"]
```

### 2.2 Despliegue con Docker Compose
```bash
docker compose -f docker/compose/docker-compose.staging.yml pull
docker compose -f docker/compose/docker-compose.staging.yml up -d --remove-orphans
```

### 2.3 Ejecución de Migraciones de Base de Datos
```bash
docker compose -f docker/compose/docker-compose.staging.yml run --rm backend alembic upgrade head
```

---

## 3. Pipeline de Promoción CI/CD

El workflow de GitHub Actions (`.github/workflows/deploy.yml`) automatiza el despliegue hacia Staging ante cada push o merge a la rama `main`:

```text
GitHub Push (main)
        │
   Tests & Lint (backend.yml, frontend.yml)
        │
   Security Scan (Trivy, Bandit, npm audit)
        │
   Build & Push GHCR Images (ghcr.io/...:staging)
        │
        ▼
   Deploy to Staging Server (SSH / Docker Compose)
        │
   Smoke Tests & Ready Check (/health/ready)
        │
   Aprobación Manual de Release
        │
        ▼
   Promoción a Producción (ghcr.io/...:v1.0.0)
```

---

## 4. Checklist de Validación en Staging

Antes de autorizar la promoción a Producción:
- [ ] Endpoint `/health/ready` responde `200 OK` con base de datos, Redis y MinIO listos.
- [ ] Las migraciones de Alembic se aplican linealmente sin errores.
- [ ] El script de auditoría pasa con cero observaciones: `python infrastructure/scripts/security-audit.py`.
- [ ] Pruebas E2E de Playwright sobre `https://staging.mercadoinsight.cl` finalizan con 100% de éxito.
- [ ] No se registran alertas de error en Sentry para la versión en prueba.
