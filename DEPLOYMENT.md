# Deployment

## Objetivo

Desplegar la plataforma de forma reproducible en VPS, Azure, AWS o Google Cloud con cambios minimos.

## Componentes

- Docker para empaquetado.
- Docker Compose para desarrollo local.
- NGINX como proxy reverso.
- GitHub Actions para CI/CD.
- Prometheus, Grafana y Loki para observabilidad.

## Ambientes

Cada ambiente es un overlay de `docker-compose.yml` en `docker/compose/`.

| | Development | Test | Staging | Production |
|---|---|---|---|---|
| Comando | `make dev-up` | `make test-env` | `make staging-up` | `make prod-up` |
| Overlay | `docker-compose.dev.yml` | `docker-compose.test.yml` | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| Puertos en el host | solo `127.0.0.1` | ninguno (proyecto aislado) | solo nginx `80`/`443` | solo nginx `80`/`443` |
| Logs | consola, `DEBUG` | JSON, `INFO` | JSON, `INFO` | JSON, `INFO` |
| Observabilidad | Prometheus + exporters + Grafana | Prometheus minimo (solo API) | Prometheus, Grafana, Alertmanager, Sentry, OTel | Prometheus, Grafana, Alertmanager, Loki/Promtail, Sentry, OTel |
| Secretos | `docker/compose/.env.*` (locales) | idem dev / sintéticos | `--env-file .env.staging`, sin defaults | `--env-file .env.prod`, sin defaults |

### Development

- `make dev-up` (o `docker compose -f docker-compose.yml -f docker/compose/docker-compose.dev.yml up -d --build`).
- Hot reload de la API (`uvicorn --reload`), pgAdmin y RedisInsight incluidos.
- Alertmanager, Loki y Promtail son opcionales: agregar `--profile observability-full`.
- `etl-worker` (cola `market-insight`) y `etl-beat` (scheduler) ejecutan la ingesta periodica; sin ellos `etl_runs` queda vacio y la
  frescura de datos no se puede medir. Los workers usan el pool `threads` y publican `/metrics` en el puerto 8000.

### Test

- `make test-env` (`infrastructure/scripts/test-env.sh`): levanta un stack desechable (proyecto `mercadoinsight-test`),
  verifica `/health/live` y `/health/ready`, comprueba que Prometheus scrapea la API, corre `pytest`, guarda los logs y lo destruye.
- Verifica ademas el flujo de alertas: reglas cargadas y probadas con `promtool`, Prometheus conectado a Alertmanager, entrega al webhook de la API,
  deduplicacion y silenciamiento. El ETL programado no corre en este ambiente (no llama a ChileCompra).
- Artefactos en `test-results/`: `junit.xml` y `logs/*.log`. El exit code es distinto de 0 si algo falla.
- `make alert-tests` ejecuta solo los tests unitarios de las reglas de alerta (`docker/monitoring/prometheus/tests/`).

### Staging

- `make staging-up` (`docker compose --env-file .env.staging -f docker-compose.yml -f docker/compose/docker-compose.staging.yml up -d --build`).
- Réplica fiel de producción: único punto de entrada público NGINX (TLS en puerto 443 con redirect de 80).
- Servicios de base de datos, caché, API y observabilidad en red interna privada.
- Herramientas dev (`pgAdmin`, `RedisInsight`) desactivadas.
- Requiere `.env.staging` (ver plantilla [.env.staging.example](file:///c:/Users/artut/market-insight/.env.staging.example)).
- Validación previa: `make staging-config`.

### Production

Servicio publico unico: **nginx** (TLS). PostgreSQL, Redis, MinIO, API, workers, Prometheus, Loki y exporters solo en red interna.
Grafana (`/grafana/`) y Alertmanager (`/alertmanager/`) salen por nginx con basic auth; Prometheus no se expone. pgAdmin y RedisInsight no se despliegan.

Antes del primer despliegue:

1. `cp .env.prod.example .env.prod` y completar **todos** los valores (ver comentarios del archivo).
2. Certificado TLS en `docker/nginx/certs/fullchain.pem` y `privkey.pem`.
3. Usuarios basic auth: `docker run --rm httpd:2.4-alpine htpasswd -nbB <usuario> <clave> > docker/nginx/auth/.htpasswd`.
4. Alertmanager: completar en `.env.prod` `ALERT_SMTP_HOST` (`host:port`), `ALERT_SMTP_USER`, `ALERT_SMTP_PASSWORD`,
   `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO` y `ALERT_WEBHOOK_TOKEN` (`openssl rand -hex 24`). La configuracion se renderiza desde
   `docker-compose.prod.yml`; las dos claves se montan como archivos (`/run/secrets`), nunca inline. `critical` y `warning` llegan por
   email; `info` solo queda en los logs.
5. `make prod-config` valida la configuracion; `make prod-up` despliega.

## Documentación Detallada de Despliegue

- [Estrategia de Entornos (Fase 10.1)](file:///c:/Users/artut/market-insight/docs/deployment/environments.md): Especificación de entornos, asignación de CPU/RAM, políticas de datos y pipeline de promoción.
- [Gestión de Configuración (Fase 10.2)](file:///c:/Users/artut/market-insight/docs/deployment/configuration.md): Taxonomía 12-factor, tipos, variables requeridas y validación automática con `validate-env.py`.
- [Gestión de Secretos (Fase 10.3)](file:///c:/Users/artut/market-insight/docs/deployment/secrets-management.md): Evaluación de Docker Secrets vs Vault vs Cloud, rotación paso a paso de credenciales y prevención de fugas.
- [Docker en Producción (Fase 10.4)](file:///c:/Users/artut/market-insight/docs/deployment/docker-production.md): Multi-stage builds, usuario no-root, optimización de imágenes y healthchecks.
- [NGINX Reverse Proxy (Fase 10.5)](file:///c:/Users/artut/market-insight/docs/deployment/nginx-reverse-proxy.md): Enrutamiento unificado, rate limiting, compresión gzip, streaming SSE para IA y security headers.
- [HTTPS / TLS (Fase 10.6)](file:///c:/Users/artut/market-insight/docs/deployment/https-ssl.md): Estándares criptográficos TLS 1.2/1.3, renovación desatendida con Let's Encrypt y certificados de prueba.
- [Estrategia de DNS (Fase 10.7)](file:///c:/Users/artut/market-insight/docs/deployment/dns-strategy.md): Dominio unificado vs subdominios, registros DNS de producción (A, CNAME, CAA, SPF/DMARC) y políticas de TTL.
- [Arquitectura CI/CD (Fase 10.8)](file:///c:/Users/artut/market-insight/docs/deployment/ci-cd.md): Orquestación con GitHub Actions, publicación en GHCR, despliegue a staging y production gate.
- [Pipeline de Backend (Fase 10.9)](file:///c:/Users/artut/market-insight/docs/deployment/pipeline-backend.md): Ruff, Mypy, Pytest, Bandit, Pip-Audit y build de contenedores.
- [Pipeline de Frontend (Fase 10.10)](file:///c:/Users/artut/market-insight/docs/deployment/pipeline-frontend.md): npm ci, ESLint, TypeScript, Vitest, Vite build, Playwright y NGINX Alpine.
- [Escaneo de Seguridad (Fase 10.11)](file:///c:/Users/artut/market-insight/docs/deployment/security-scan.md): Escaneo de imágenes con Trivy, detección de secretos, SARIF y bloqueo por severidad.
- [Estrategia de Versionado (Fase 10.12)](file:///c:/Users/artut/market-insight/docs/deployment/versioning.md): SemVer 2.0.0, CHANGELOG Keep a Changelog, tags Git y release tracking en Sentry.
- [Migraciones de Base de Datos (Fase 10.13)](file:///c:/Users/artut/market-insight/docs/deployment/database-migrations.md): Árbol de revisiones Alembic, patrón Expand/Contract para zero-downtime y rollback.
- [Estrategia de Backups (Fase 10.14)](file:///c:/Users/artut/market-insight/docs/deployment/backup-strategy.md): Respaldo de PostgreSQL con pg_dump comprimido, MinIO, retención y script de automatización.
- [Plan de Recuperación ante Desastres (Fase 10.15)](file:///c:/Users/artut/market-insight/DISASTER_RECOVERY.md): Manual de contingencia, RTO/RPO, runbooks operacionales y script de restauración verificada.
- [Definición de RPO / RTO (Fase 10.16)](file:///c:/Users/artut/market-insight/docs/deployment/rpo-rto.md): Justificación técnica, supuestos de infraestructura y validación mediante simulación.
- [Observabilidad Final (Fase 10.17)](file:///c:/Users/artut/market-insight/docs/deployment/observability-final.md): Stack unificado Prometheus, Grafana, Alertmanager, Loki, Sentry y OpenTelemetry.
- [Monitoreo de Costos de IA (Fase 10.18)](file:///c:/Users/artut/market-insight/docs/deployment/ai-cost-monitoring.md): Catálogo de tarifas por modelo, registro granular de tokens y alertas de consumo.
- [Auditoría de Seguridad y Hardening (Fase 10.19)](file:///c:/Users/artut/market-insight/docs/deployment/security-audit.md): Checklist de seguridad, verificación de puertos y script de auditoría.
- [Arquitectura de Red (Fase 10.20)](file:///c:/Users/artut/market-insight/docs/deployment/network-architecture.md): Segmentación en dos niveles (public-net y private-net) en Docker Compose.
- [Estructura de Documentación Técnica (Fase 10.21)](file:///c:/Users/artut/market-insight/docs/architecture/overview.md): Guías de arquitectura, despliegue, datos, IA y operaciones.
- [Portal Principal README (Fase 10.22)](file:///c:/Users/artut/market-insight/README.md): Portal maestro del proyecto con las 16 secciones consolidadas.
- [Modelo C4 de Arquitectura (Fase 10.23)](file:///c:/Users/artut/market-insight/ARCHITECTURE.md): Diagramas formales C4 (Contexto, Contenedores, Componentes).
- [Especificación OpenAPI y Consumo (Fase 10.24)](file:///c:/Users/artut/market-insight/API.md): Contratos de API, JWT, paginación, filtros y streaming SSE.
- [Runbooks y Gestión de Incidentes (Fase 10.25)](file:///c:/Users/artut/market-insight/docs/operations/troubleshooting.md): Protocolos de mitigación (API caída, ETL detenido, Postgres lleno) y matriz de severidad.
- [Guía de Usuario y Documentación Funcional (Fase 10.26)](file:///c:/Users/artut/market-insight/docs/user-guide/getting-started.md): Manuales funcionales para dashboard, búsqueda, proveedores y análisis.
- [Manual de MercadoInsight AI (Fase 10.27)](file:///c:/Users/artut/market-insight/docs/ai/manual.md): Principio rector de fuente primaria, RAG, Text-to-SQL, fuentes citadas y guardrails.
- [Architecture Decision Records - ADR (Fase 10.28)](file:///c:/Users/artut/market-insight/docs/adr/README.md): Registro de 14 decisiones arquitectónicas estructuradas.
- [Checklist y Puerta de Control de Release (Fase 10.29)](file:///c:/Users/artut/market-insight/docs/deployment/release-checklist.md): Release gate formal automatizado con script de validación.

## Consideraciones

- No embutir secretos en imagenes (`.dockerignore` activo).
- Separar build de runtime (multi-stage builds).
- Limitar acceso a los servicios internos (loopback o red interna privada).
- Monitorear jobs, colas y errores de integracion.
