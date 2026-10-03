# Arquitectura CI/CD con GitHub Actions — MercadoInsight

Este documento detalla la arquitectura de Integración y Despliegue Continuo (CI/CD) de **MercadoInsight** implementada sobre **GitHub Actions** para el repositorio [https://github.com/ernestostarck/market-insight](https://github.com/ernestostarck/market-insight).

---

## 1. Visión General del Pipeline

El sistema automatiza todas las fases de calidad de código, pruebas, escaneo de seguridad, empaquetado de contenedores y despliegue progresivo:

```text
                                 Developer Git Push
                                          │
                                          ▼
                                ┌───────────────────┐
                                │   GitHub Actions  │
                                └───────────────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
          ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
          │  backend.yml  │       │  frontend.yml │       │  security.yml │
          │ Linter, Types,│       │ ESLint, Types,│       │ Trivy, Secret │
          │ Tests, Bandit │       │ Vitest, Build │       │ Audit, SARIF  │
          └───────────────┘       └───────────────┘       └───────────────┘
                  │                       │                       │
                  └───────────────────────┼───────────────────────┘
                                          ▼ (Todos exitosos en main)
                                ┌───────────────────┐
                                │ GitHub Container  │
                                │  Registry (GHCR)  │
                                └───────────────────┘
                                          │
                                          ▼
                                ┌───────────────────┐
                                │  Despliegue a     │
                                │     Staging       │
                                └───────────────────┘
                                          │
                                          ▼ (Smoke Tests OK)
                                ┌───────────────────┐
                                │ Aprobación Manual │
                                │ (Production Gate) │
                                └───────────────────┘
                                          │
                                          ▼
                                ┌───────────────────┐
                                │  Despliegue a     │
                                │   Producción      │
                                └───────────────────┘
```

---

## 2. Estructura de Workflows

Los flujos de trabajo están desacoplados por dominio en [`.github/workflows/`](file:///c:/Users/artut/market-insight/.github/workflows/):

| Workflow | Archivo | Triggers | Propósito |
| :--- | :--- | :--- | :--- |
| **Backend** | [`backend.yml`](file:///c:/Users/artut/market-insight/.github/workflows/backend.yml) | Push / PR en `apps/backend/**` | Lint (`ruff`), tipos (`mypy`), tests (`pytest`), SAST (`bandit`), dependencias (`pip-audit`), build y push Docker. |
| **Frontend** | [`frontend.yml`](file:///c:/Users/artut/market-insight/.github/workflows/frontend.yml) | Push / PR en `apps/frontend/**` | `npm ci`, lint (`eslint`), tipos (`tsc`), tests (`vitest`), build Vite, pruebas E2E Playwright, build y push Docker. |
| **Security** | [`security.yml`](file:///c:/Users/artut/market-insight/.github/workflows/security.yml) | Push en `main`, PRs, Schedule semanal | Escaneo de vulnerabilidades en imágenes y código con Trivy, detección de secretos y reporte SARIF en GitHub Security. |
| **Deploy** | [`deploy.yml`](file:///c:/Users/artut/market-insight/.github/workflows/deploy.yml) | Completación en `main`, Tags `v*`, Manual | Despliegue automático a Staging, smoke tests, y despliegue con aprobación a Producción. |

---

## 3. Registro de Contenedores (GHCR)

Las imágenes se publican en **GitHub Container Registry (GHCR)** bajo el namespace del repositorio:

* **Backend API**: `ghcr.io/ernestostarck/market-insight/backend`
* **Celery Worker**: `ghcr.io/ernestostarck/market-insight/worker`
* **Frontend SPA**: `ghcr.io/ernestostarck/market-insight/frontend`

### Estrategia de Etiquetado (Tags)
1. **Commit SHA (`short_sha`)**: Permite trazabilidad inmutable y rollback determinista a cualquier commit específico.
2. **`latest`**: Apunta siempre al último build exitoso de la rama `main`.
3. **Versión Semántica (`vX.Y.Z`)**: Generado automáticamente ante la creación de un tag Git para releases formales.

---

## 4. Pipeline de Despliegue y Ambientes

### 4.1 Entorno Staging (Automático)
* Cuando los pipelines de backend, frontend y seguridad finalizan exitosamente en la rama `main`, `deploy.yml` despliega en el servidor de Staging.
* **Smoke Tests**: Se ejecutan pruebas de comprobación de salud contra `/health/live` y `/health/ready`. Si los smoke tests fallan, el pipeline emite una alerta.

### 4.2 Entorno Producción (Con Aprobación Requerida)
* Configurado en GitHub bajo **Environment: `production`**.
* **Quality Gate Obligatorio**: Requiere la revisión y firma manual de los administradores del repositorio antes de iniciar la actualización de producción.
* **Proceso de Despliegue**:
  1. Pull de las imágenes de contenedor verificadas desde GHCR.
  2. Ejecución de migraciones de base de datos (`alembic upgrade head`).
  3. Rolling restart de los contenedores con Docker Compose.
  4. Verificación perimetral HTTPS contra `https://mercadoinsight.cl/health`.

### 4.3 Estrategia de Rollback
Si los smoke tests post-despliegue detectan anomalías o una tasa elevada de respuestas HTTP 5xx:
* El workflow de despliegue ejecuta el job de rollback restaurando el SHA anterior de los contenedores.
* Para rollback manual inmediato desde terminal en el servidor:
  ```bash
  # Desplegar versión estable anterior
  export IMAGE_TAG=<SHA_ANTERIOR>
  docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml up -d
  ```

---

## 5. Estrategia de Ramas (Trunk-Based Development)

MercadoInsight utiliza **Trunk-Based Development** como modelo de integración continua:

* **Rama Principal (`main`)**: Siempre desplegable a producción. Todo cambio ingresa vía Pull Request de vida corta (`feat/*`, `fix/*`, `chore/*`).
* **Protección de Rama (`main`)**:
  * Requiere al menos 1 aprobación (code review) para merge.
  * Requiere que pasen exitosamente todos los status checks requeridos (`lint-and-types`, `test-and-coverage`, `unit-tests`, `build`).
  * Requiere historial lineal (Squash and merge).
* **Tags de Release**: Formato `vX.Y.Z` disparan despliegues directos a producción tras el gate de aprobación.

---

## 6. Inventario de GitHub Secrets y Environments

Para la ejecución segura de los pipelines y despliegues, se configuran los siguientes secretos en el repositorio:

| Secreto / Variable | Ámbito | Descripción |
| :--- | :--- | :--- |
| `GITHUB_TOKEN` | Automático | Token generado por GitHub Actions para autenticar en GHCR y Code Scanning. |
| `STAGING_SSH_KEY` | Environment `staging` | Clave privada SSH para orquestar pull y restart en servidor Staging. |
| `STAGING_HOST` | Environment `staging` | IP o hostname del servidor de Staging. |
| `PROD_SSH_KEY` | Environment `production` | Clave privada SSH para orquestar pull y restart en servidor Producción. |
| `PROD_HOST` | Environment `production` | IP o hostname del servidor de Producción (`mercadoinsight.cl`). |
| `SLACK_WEBHOOK_URL` | Repositorio | Notificaciones automáticas de fallos en producción y alertas de seguridad. |

