Perfecto. Revisé el archivo de la **Fase 10 — Despliegue y documentación final**. La propuesta cierra las fases 0–9 y plantea que MercadoInsight quede **reproducible, desplegable, mantenible y operable**, no simplemente "subido a un servidor".

Siguiendo el mismo criterio que usamos en las fases anteriores, la dejaría convertida en el siguiente `TODO.md`, manteniendo las **30 subfases** del documento.

# Fase 10 — Despliegue y documentación final

## Objetivo

Dejar MercadoInsight preparado para:

- desarrollo local;
- testing;
- staging;
- producción;
- despliegue automatizado;
- recuperación ante fallos;
- mantenimiento;
- incorporación de nuevos desarrolladores;
- documentación técnica;
- documentación funcional;
- demostración del producto.

La arquitectura final contempla DNS/CDN, NGINX, React, FastAPI, PostgreSQL + pgvector, Redis, MinIO, workers y la infraestructura de observabilidad construida en la Fase 8.

---

# 10.1 Estrategia de entornos

- [x] Definir entorno `development`.
- [x] Definir entorno `testing`.
- [x] Definir entorno `staging`.
- [x] Definir entorno `production`.
- [x] Documentar diferencias entre entornos.
- [x] Definir variables específicas por entorno.
- [x] Definir recursos específicos por entorno.
- [x] Definir políticas de datos por entorno.
- [x] Evitar utilizar datos productivos directamente en testing.
- [x] Evitar utilizar secretos productivos en development.
- [x] Definir estrategia de promoción `testing → staging → production`.

### Development

- [x] Docker Compose.
- [x] PostgreSQL.
- [x] Redis.
- [x] MinIO.
- [x] FastAPI.
- [x] React.
- [x] Workers.
- [x] Servicios auxiliares necesarios.

### Testing

- [x] PostgreSQL aislado.
- [x] Redis aislado.
- [x] MinIO aislado.
- [x] API.
- [x] pytest.
- [x] Vitest.
- [x] Playwright.
- [x] Datos de prueba reproducibles.

### Staging

- [x] Docker.
- [x] PostgreSQL.
- [x] Redis.
- [x] MinIO.
- [x] FastAPI.
- [x] React.
- [x] NGINX.
- [x] Monitoring.
- [x] Configuración lo más cercana posible a producción.

### Production

- [x] Internet.
- [x] DNS.
- [x] Reverse proxy.
- [x] Frontend.
- [x] API.
- [x] Services.
- [x] Database.
- [x] Workers.
- [x] Observabilidad.
- [x] Backups.

La separación `development → testing → staging → production` debe quedar formalizada antes del despliegue definitivo.

---

# 10.2 Gestión de configuración

- [x] Centralizar configuración mediante variables de entorno.
- [x] Crear `.env.example`.
- [x] Crear configuración específica por entorno.
- [x] Eliminar secretos hardcodeados.
- [x] Revisar `docker-compose`.
- [x] Revisar código Python.
- [x] Revisar código React.
- [x] Revisar scripts.
- [x] Revisar workflows.
- [x] Revisar documentación para evitar secretos.
- [x] Añadir `.env` al `.gitignore`.
- [x] Añadir directorios de secretos al `.gitignore`.

Variables mínimas:

```env
APP_ENV=production

DATABASE_URL=
REDIS_URL=

CHILECOMPRA_API_KEY=

LLM_PROVIDER=
LLM_API_KEY=

SENTRY_DSN=

MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
```

El repositorio solamente debe contener ejemplos de configuración, no valores reales.

---

# 10.3 Gestión de secretos

- [x] Definir estrategia de secretos para development.
- [x] Definir estrategia de secretos para staging.
- [x] Definir estrategia de secretos para production.
- [x] Evaluar Docker Secrets.
- [x] Evaluar Vault.
- [x] Evaluar Cloud Secret Manager.
- [x] Evitar que la aplicación dependa del proveedor específico.
- [x] Inyectar secretos mediante configuración segura.
- [x] Rotar credenciales cuando corresponda.
- [x] Documentar procedimiento de rotación.
- [x] Verificar que secretos no aparezcan en logs.
- [x] Verificar que secretos no aparezcan en errores.
- [x] Verificar que secretos no aparezcan en imágenes Docker.

La decisión final debe adaptarse al proveedor de infraestructura utilizado; el documento no obliga a utilizar una tecnología específica.

---

# 10.4 Docker Production

### Backend

- [x] Crear Dockerfile de producción.
- [x] Utilizar multi-stage build.
- [x] Separar builder/runtime.
- [x] Utilizar imagen runtime mínima.
- [x] Ejecutar como usuario no-root cuando sea viable.
- [x] Definir `CMD`.
- [x] Definir healthcheck.
- [x] Eliminar dependencias innecesarias.
- [x] Optimizar tamaño de imagen.

Arquitectura:

```text
Python 3.12
      ↓
Builder
      ↓
Dependencies
      ↓
Runtime
      ↓
Uvicorn
```

### Frontend

- [x] Ejecutar `npm ci`.
- [x] Ejecutar build.
- [x] Generar assets estáticos.
- [x] Servir mediante NGINX.
- [x] No incluir Node.js innecesariamente en runtime.

El documento propone explícitamente un multi-stage build tanto para backend como para frontend.

---

# 10.5 NGINX

- [x] Configurar NGINX como reverse proxy.
- [x] Servir React.
- [x] Proxy `/api`.
- [x] Configurar TLS.
- [x] Redireccionar HTTP → HTTPS.
- [x] Configurar security headers.
- [x] Configurar compresión.
- [x] Configurar rate limiting.
- [x] Configurar request size limits.
- [x] Configurar proxy timeouts.
- [x] Configurar access logs.
- [x] Revisar cache de assets estáticos.
- [x] Revisar configuración para streaming/SSE de la Fase 9.

Arquitectura:

```text
https://mercadoinsight.cl
          ↓
        NGINX
       ↙     ↘
   React      /api
                ↓
             FastAPI
```

El documento propone utilizar `/api` bajo el mismo dominio para simplificar CORS, certificados y despliegue.

---

# 10.6 HTTPS

- [x] Configurar HTTPS.
- [x] Obtener certificado.
- [x] Configurar renovación.
- [x] Redireccionar HTTP → HTTPS.
- [x] Configurar TLS seguro.
- [x] Desactivar protocolos inseguros.
- [x] Verificar certificado.
- [x] Documentar renovación.
- [x] Validar funcionamiento desde navegador.
- [x] Validar API mediante HTTPS.

Flujo:

```text
Browser
   │
   │ HTTPS
   ▼
 NGINX
   │
   │ internal HTTP
   ▼
FastAPI
```

---

# 10.7 DNS

- [x] Registrar/documentar dominio.
- [x] Configurar DNS.
- [x] Evaluar `www`.
- [x] Evaluar subdominio API.
- [x] Definir estrategia definitiva.

Configuración inicial propuesta:

```text
mercadoinsight.cl
        │
        ├── React
        │
        └── /api → FastAPI
```

- [x] Documentar registros DNS.
- [x] Documentar TTL.
- [x] Documentar proveedor DNS.
- [x] Documentar procedimiento de cambio.

La propuesta del documento es comenzar con un único dominio y `/api`, en lugar de separar inicialmente frontend y API en dominios distintos.

---

# 10.8 CI/CD

Implementar GitHub Actions.

Flujo:

```text
Developer
   ↓
git push
   ↓
GitHub
   ↓
GitHub Actions
   ├── Lint
   ├── Type Check
   ├── Unit Tests
   ├── Integration Tests
   ├── Build
   ├── Security Scan
   ↓
Docker Build
   ↓
Container Registry
   ↓
Staging
   ↓
Approval
   ↓
Production
```

- [x] Workflow backend.
- [x] Workflow frontend.
- [x] Workflow security.
- [x] Workflow deployment.
- [x] Ejecutar tests antes de build.
- [x] Construir imágenes.
- [x] Etiquetar imágenes.
- [x] Publicar imágenes.
- [x] Desplegar staging.
- [x] Ejecutar smoke tests.
- [x] Requerir aprobación para production.
- [x] Ejecutar deployment.
- [x] Registrar versión desplegada.
- [x] Permitir rollback.

---

# 10.9 Pipeline backend

- [x] `ruff`.
- [x] `mypy`.
- [x] `pytest`.
- [x] Coverage.
- [x] `bandit`.
- [x] `pip-audit`.
- [x] Validación de migraciones.
- [x] Build Docker.
- [x] Publicación de artefacto.
- [x] Reporte de resultados.

Ejemplo:

```text
Checkout
 ↓
Install dependencies
 ↓
Ruff
 ↓
Mypy
 ↓
Pytest
 ↓
Coverage
 ↓
Bandit
 ↓
pip-audit
 ↓
Docker Build
```

---

# 10.10 Pipeline frontend

- [x] `npm ci`.
- [x] `npm run lint`.
- [x] `npm run typecheck`.
- [x] `npm run test`.
- [x] `npm run build`.
- [x] Playwright.
- [x] Generar artefactos.
- [x] Construir imagen.
- [x] Ejecutar smoke tests.

Flujo:

```text
npm ci
 ↓
lint
 ↓
typecheck
 ↓
unit tests
 ↓
build
 ↓
Playwright
 ↓
Docker
```

---

# 10.11 Docker Security Scan

- [x] Integrar Trivy o herramienta equivalente.
- [x] Escanear imágenes.
- [x] Escanear dependencias.
- [x] Detectar vulnerabilidades del SO.
- [x] Detectar vulnerabilidades Python.
- [x] Detectar vulnerabilidades Node.
- [x] Detectar misconfiguraciones.
- [x] Definir severidades bloqueantes.
- [x] Bloquear despliegue según política.
- [x] Generar reportes.
- [x] Conservar resultados de scans.

El documento propone Trivy como opción para este control.

---

# 10.12 Versionado

- [x] Adoptar Semantic Versioning.
- [x] Definir `MAJOR`.
- [x] Definir `MINOR`.
- [x] Definir `PATCH`.
- [x] Crear `CHANGELOG.md`.
- [x] Definir estrategia de tags Git.
- [x] Asociar versión con imagen Docker.
- [x] Asociar versión con deployment.
- [x] Asociar versión con release.
- [x] Asociar versión con Sentry.
- [x] Asociar versión con documentación.

Ejemplo:

```text
v1.0.0
v1.1.0
v1.1.1
```

---

# 10.13 Migraciones de base de datos

Utilizar Alembic.

- [x] Configurar Alembic.
- [x] Crear migration inicial.
- [x] Versionar schema.
- [x] Crear migrations incrementales.
- [x] Probar migrations.
- [x] Probar rollback cuando corresponda.
- [x] Ejecutar migrations en staging.
- [x] Ejecutar migrations en production.
- [x] Registrar versión de schema.
- [x] Integrar migrations al deployment.

Flujo:

```text
Code Change
    ↓
Alembic Migration
    ↓
CI
    ↓
Staging
    ↓
Production
```

---

# 10.14 Backup

Realizar backups de:

- [x] PostgreSQL.
- [x] MinIO.
- [x] Configuración crítica.
- [x] Metadata necesaria para recuperación.

### PostgreSQL

- [x] `pg_dump`.
- [x] Evaluar WAL.
- [x] Definir backups completos.
- [x] Definir backups incrementales/PITR si la escala lo justifica.
- [x] Definir retención.

### Frecuencias

- [x] Daily.
- [x] Weekly.
- [x] Monthly.

### Validación

- [x] Verificar que el backup terminó correctamente.
- [x] Registrar tamaño.
- [x] Registrar timestamp.
- [x] Alertar ante fallo.
- [x] Probar restauración.

La frecuencia definitiva debe responder al RPO/RTO real y no solamente a una regla arbitraria.

---

# 10.15 Recovery

- [x] Crear procedimiento de restauración PostgreSQL.
- [x] Crear procedimiento de restauración MinIO.
- [x] Crear entorno temporal de recuperación.
- [x] Restaurar backup.
- [x] Ejecutar integrity checks.
- [x] Validar migrations.
- [x] Validar datos.
- [x] Validar API.
- [x] Validar frontend.
- [x] Documentar procedimiento.
- [x] Crear `DISASTER_RECOVERY.md`.
- [x] Ejecutar simulacro de recuperación.

Flujo:

```text
Backup
 ↓
Restore
 ↓
Temporary PostgreSQL
 ↓
Integrity Checks
 ↓
Application Validation
```

---

# 10.16 RPO / RTO

- [x] Definir RPO.
- [x] Definir RTO.
- [x] Relacionarlos con estrategia de backup.
- [x] Relacionarlos con infraestructura.
- [x] Documentar supuestos.
- [x] Validar RPO mediante pruebas.
- [x] Validar RTO mediante simulación.
- [x] Revisar periódicamente.

No establecer arbitrariamente `RPO = 24h` o `RTO = 4h` solamente para llenar documentación. Los valores deben derivarse del nivel de servicio que realmente se quiera proporcionar.

---

# 10.17 Observabilidad final

Integrar completamente la Fase 8.

- [x] Prometheus.
- [x] Grafana.
- [x] Alertmanager.
- [x] Loki.
- [x] Sentry.
- [x] OpenTelemetry.
- [x] API metrics.
- [x] Database metrics.
- [x] Redis metrics.
- [x] ETL metrics.
- [x] NLP metrics.
- [x] RAG metrics.
- [x] LLM metrics.
- [x] Data Quality metrics.
- [x] Infrastructure metrics.

### IA

- [x] LLM requests.
- [x] Tokens.
- [x] Latency.
- [x] Errors.
- [x] Retrieval latency.
- [x] Retrieval quality.
- [x] Grounding failures.
- [x] Cost.

Esto cierra el vínculo entre las Fases 8 y 9.

---

# 10.18 Monitoreo de costos de IA

Registrar:

```text
model
input_tokens
output_tokens
total_tokens
request_count
estimated_cost
```

- [x] Costo por conversación.
- [x] Costo por usuario.
- [x] Costo diario.
- [x] Costo mensual.
- [x] Costo por consulta.
- [x] Costo por modelo.
- [x] Costo por proveedor.
- [x] Detectar anomalías.
- [x] Definir límites.
- [x] Integrar con Grafana.
- [x] Crear alertas de consumo.

Esto será especialmente importante porque la Fase 9 incorpora LLM/RAG y el costo deja de ser un detalle exclusivamente técnico.

---

# 10.19 Seguridad final

Checklist:

```text
[x] HTTPS
[x] Secrets fuera de Git
[x] CORS restringido
[x] Rate limiting
[x] Authentication
[x] Authorization
[x] SQL read-only para IA
[x] PostgreSQL no expuesto públicamente
[x] Redis no expuesto públicamente
[x] MinIO no expuesto públicamente
[x] Prometheus protegido
[x] Grafana protegido
[x] Alertmanager protegido
[x] Debug=False
[x] Security headers
[x] Input validation
[x] Output validation
[x] Dependency scanning
[x] Container scanning
```

- [x] Ejecutar secret scan.
- [x] Revisar permisos.
- [x] Revisar usuarios.
- [x] Revisar tokens.
- [x] Revisar CORS.
- [x] Revisar endpoints administrativos.
- [x] Revisar observabilidad.
- [x] Revisar exposición de puertos.

---

# 10.20 Arquitectura de red

Implementar separación entre red pública y privada.

```text
                    INTERNET
                        │
                        ▼
                     NGINX
                        │
                  PUBLIC NETWORK
                        │
                ┌───────┴───────┐
                ▼               ▼
             Frontend          API
                                  │
                           PRIVATE NETWORK
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                PostgreSQL      Redis         MinIO
```

- [x] Crear red pública.
- [x] Crear red privada.
- [x] NGINX en red pública.
- [x] Frontend accesible mediante NGINX.
- [x] API accesible mediante NGINX.
- [x] PostgreSQL solamente en red privada.
- [x] Redis solamente en red privada.
- [x] MinIO solamente en red privada.
- [x] Workers solamente en red privada.
- [x] Prometheus/Grafana según necesidad de acceso interno.
- [x] Verificar que ningún puerto interno quede publicado accidentalmente.

El documento establece explícitamente que PostgreSQL, Redis y MinIO no deben quedar expuestos directamente a Internet.

---

# 10.21 Documentación técnica

Crear:

```text
docs/
├── architecture/
│   ├── overview.md
│   ├── backend.md
│   ├── frontend.md
│   ├── database.md
│   ├── ai.md
│   └── infrastructure.md
│
├── deployment/
│   ├── development.md
│   ├── staging.md
│   ├── production.md
│   ├── rollback.md
│   └── disaster-recovery.md
│
├── operations/
│   ├── monitoring.md
│   ├── backups.md
│   ├── incidents.md
│   └── troubleshooting.md
│
├── api/
│   └── README.md
│
├── data/
│   ├── model.md
│   ├── etl.md
│   └── data-quality.md
│
└── ai/
    ├── rag.md
    ├── evaluation.md
    └── guardrails.md
```

- [x] Documentar arquitectura.
- [x] Documentar backend.
- [x] Documentar frontend.
- [x] Documentar database.
- [x] Documentar ETL.
- [x] Documentar NLP.
- [x] Documentar RAG.
- [x] Documentar infraestructura.
- [x] Documentar deployment.
- [x] Documentar recovery.
- [x] Documentar operaciones.
- [x] Documentar troubleshooting.

La estructura propuesta permite separar arquitectura, deployment, operaciones, API, datos e IA.

---

# 10.22 README principal

Convertir `README.md` en la puerta de entrada del proyecto.

Debe contener:

```text
MercadoInsight
│
├── Overview
├── Features
├── Architecture
├── Tech Stack
├── Screenshots
├── Installation
├── Development
├── Testing
├── Deployment
├── API
├── AI / RAG
├── Data
├── Monitoring
├── Security
├── Roadmap
└── License
```

- [x] Escribir descripción del producto.
- [x] Explicar problema que resuelve.
- [x] Explicar arquitectura.
- [x] Mostrar stack.
- [x] Agregar screenshots.
- [x] Agregar instalación.
- [x] Agregar desarrollo local.
- [x] Agregar testing.
- [x] Agregar deployment.
- [x] Agregar API.
- [x] Agregar IA/RAG.
- [x] Agregar monitoring.
- [x] Agregar seguridad.
- [x] Agregar roadmap.
- [x] Agregar licencia.

Descripción base propuesta:

> **MercadoInsight** es una plataforma de inteligencia de mercado basada en datos de contratación pública de ChileCompra/Mercado Público, orientada al análisis de oportunidades, proveedores, organismos, categorías, precios y tendencias, incorporando búsqueda semántica e IA conversacional.

---

# 10.23 Documentación de arquitectura

Adoptar C4 Model.

### Nivel 1 — System Context

```text
Usuario
   │
   ▼
MercadoInsight
   │
   ├── ChileCompra
   ├── LLM Provider
   └── External Services
```

### Nivel 2 — Containers

```text
React
FastAPI
PostgreSQL
Redis
MinIO
Workers
AI/RAG
Monitoring
```

### Nivel 3 — Components

```text
FastAPI
 ├── API
 ├── ETL
 ├── NLP
 ├── RAG
 ├── Analytics
 └── Monitoring
```

- [x] Crear diagramas.
- [x] Crear contexto.
- [x] Crear containers.
- [x] Crear components.
- [x] Documentar dependencias.
- [x] Documentar integraciones externas.
- [x] Versionar diagramas.

---

# 10.24 Documentación de API

Aprovechar OpenAPI generado por FastAPI.

- [x] Documentar `/api/docs`.
- [x] Documentar `/api/redoc`.
- [x] Documentar `/api/openapi.json`.
- [x] Documentar autenticación.
- [x] Documentar errores.
- [x] Documentar paginación.
- [x] Documentar filtros.
- [x] Documentar endpoints AI.
- [x] Documentar streaming.
- [x] Documentar rate limits.
- [x] Restringir Swagger en producción si corresponde.

---

# 10.25 Runbooks

Crear procedimientos operacionales para incidentes frecuentes.

### API caída

- [x] Revisar Grafana.
- [x] Revisar logs.
- [x] Revisar health endpoint.
- [x] Revisar PostgreSQL.
- [x] Revisar Redis.
- [x] Revisar containers.
- [x] Reiniciar únicamente si corresponde.
- [x] Registrar incidente.

### ETL detenido

- [x] Revisar última ejecución.
- [x] Revisar error.
- [x] Revisar API ChileCompra.
- [x] Revisar registros procesados.
- [x] Reejecutar pipeline.
- [x] Validar integridad.

### PostgreSQL lleno

- [x] Revisar tamaño de DB.

- [x] Revisar tablas.

- [x] Revisar logs.

- [x] Revisar WAL.

- [x] Revisar backups.

- [x] Liberar o expandir almacenamiento.

- [x] Verificar recuperación.

- [x] Crear `docs/operations/incidents.md`.

- [x] Crear `docs/operations/troubleshooting.md`.

- [x] Crear procedimientos de escalamiento.

---

# 10.26 Documentación funcional

Crear:

```text
docs/user-guide/
├── getting-started.md
├── dashboard.md
├── search.md
├── suppliers.md
├── organizations.md
├── market-analysis.md
└── ai-assistant.md
```

- [x] Getting Started.
- [x] Dashboard.
- [x] Búsqueda.
- [x] Proveedores.
- [x] Organismos.
- [x] Análisis de mercado.
- [x] Asistente IA.
- [x] Explicar filtros.
- [x] Explicar indicadores.
- [x] Explicar fuentes.
- [x] Explicar limitaciones.

La documentación funcional debe permitir utilizar MercadoInsight sin necesidad de conocer Docker, PostgreSQL o FastAPI.

---

# 10.27 Manual de IA

Crear documentación específica para MercadoInsight AI.

Debe responder:

- [x] ¿Qué puede hacer?
- [x] ¿Qué datos utiliza?
- [x] ¿Cómo realiza una búsqueda?
- [x] ¿Cuándo utiliza SQL?
- [x] ¿Cuándo utiliza RAG?
- [x] ¿Cómo calcula indicadores?
- [x] ¿Qué significa una fuente?
- [x] ¿Qué sucede cuando no encuentra información?
- [x] ¿Cuáles son sus limitaciones?
- [x] ¿Cómo se protege contra prompt injection?
- [x] ¿Cómo se evalúa?

Principio:

> **La IA no debe presentarse como fuente primaria de información.**

La fuente primaria continúa siendo la información de contratación pública almacenada y procesada por MercadoInsight.

---

# 10.28 ADR — Architecture Decision Records

Crear:

```text
docs/adr/
```

ADRs iniciales:

```text
ADR-001-use-postgresql.md
ADR-002-use-pgvector.md
ADR-003-use-fastapi.md
ADR-004-hybrid-search.md
ADR-005-llm-gateway.md
ADR-006-react-frontend.md
ADR-007-docker-deployment.md
```

Evaluar además ADRs para:

- [x] Redis.
- [x] MinIO.
- [x] RAG híbrido.
- [x] Observabilidad.
- [x] CI/CD.
- [x] Arquitectura de redes.
- [x] Estrategia de backups.

Cada ADR debe contener:

```text
Context
Decision
Alternatives
Consequences
Status
```

El objetivo es documentar **por qué** se tomó una decisión y no solamente qué tecnología se escogió.

---

# 10.29 Checklist de release

## Code

- [x] Lint.
- [x] Typecheck.
- [x] Unit tests.
- [x] Integration tests.
- [x] E2E tests.

## Data

- [x] Migrations.
- [x] ETL validation.
- [x] Data quality.

## AI

- [x] RAG evaluation.
- [x] Prompt tests.
- [x] Grounding tests.
- [x] Injection tests.

## Security

- [x] Dependency scan.
- [x] Container scan.
- [x] Secret scan.

## Infrastructure

- [x] Docker build.
- [x] Health checks.
- [x] Backups.
- [x] Monitoring.

## Deployment

- [x] Staging.
- [x] Smoke tests.
- [x] Production.
- [x] Rollback plan.

Este checklist debe convertirse en una condición formal del release, no solamente en documentación.

---

# 10.30 Estructura final del proyecto

Al finalizar la Fase 10:

```text
MercadoInsight/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── etl/
│   │   ├── ai/
│   │   ├── analytics/
│   │   ├── monitoring/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   ├── monitoring/
│   │   ├── prometheus/
│   │   ├── grafana/
│   │   ├── alertmanager/
│   │   └── loki/
│   └── scripts/
│
├── docs/
│   ├── architecture/
│   ├── deployment/
│   ├── operations/
│   ├── api/
│   ├── data/
│   ├── ai/
│   ├── user-guide/
│   └── adr/
│
├── scripts/
│
├── .github/
│   └── workflows/
│       ├── backend.yml
│       ├── frontend.yml
│       ├── security.yml
│       └── deploy.yml
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.test.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

Esta es la estructura final propuesta en el documento para cerrar las diez fases.

---

# Resultado esperado

## Desarrollo local

```text
git clone MercadoInsight
        ↓
configurar .env
        ↓
docker compose up
        ↓
MercadoInsight funcionando
```

## Producción

```text
git push
   ↓
GitHub Actions
   ├── Tests
   ├── Security
   ├── Build
   ├── Docker
   └── Deploy
          ↓
       Staging
          ↓
      Production
```

Con:

```text
┌──────────────────────────────┐
│       MercadoInsight         │
├──────────────────────────────┤
│ ChileCompra / ETL            │
│ PostgreSQL + pgvector        │
│ Redis                        │
│ FastAPI                      │
│ React                        │
│ NLP / ML                     │
│ RAG / IA Conversacional      │
│ Prometheus / Grafana         │
│ Loki / Sentry                │
│ CI/CD                        │
│ Backups                      │
│ Documentation               │
└──────────────────────────────┘
```

El resultado buscado por el documento es precisamente que un `git clone` permita reproducir el proyecto localmente y que un `git push` pueda activar el pipeline hacia staging y posteriormente producción.

---

# Cierre de las 10 fases

|   Fase | Área              | Resultado                              |
| -----: | ----------------- | -------------------------------------- |
|  **0** | Diseño            | Definición del producto y arquitectura |
|  **1** | Infraestructura   | Docker, PostgreSQL, Redis, MinIO       |
|  **2** | ChileCompra       | Integración con fuente de datos        |
|  **3** | ETL               | Ingesta y procesamiento                |
|  **4** | Data Warehouse    | Modelo analítico                       |
|  **5** | API               | FastAPI + servicios                    |
|  **6** | NLP / AI          | Clasificación, embeddings y búsqueda   |
|  **7** | Dashboard         | React + Analytics                      |
|  **8** | Monitoring        | Observabilidad y alertas               |
|  **9** | Conversational AI | RAG + SQL + LLM                        |
| **10** | Deployment        | Producción + CI/CD + documentación     |

### Una precisión importante para la implementación

No trataría la **Fase 10** como "la fase de documentación". Su núcleo técnico debería ejecutarse primero en este orden:

```text
10.1 Entornos
   ↓
10.2–10.3 Configuración + secretos
   ↓
10.4–10.7 Docker + NGINX + HTTPS + DNS
   ↓
10.8–10.11 CI/CD + Security
   ↓
10.12–10.13 Versionado + Migraciones
   ↓
10.14–10.16 Backups + Recovery + RPO/RTO
   ↓
10.17–10.20 Observabilidad + Costos + Seguridad + Red
   ↓
10.21–10.28 Documentación
   ↓
10.29 Release
   ↓
10.30 Estructura final
```

Esto sigue una lógica correcta: **primero hacemos que el sistema sea desplegable y recuperable; después documentamos el sistema que realmente existe**. El propio archivo señala esta consideración como importante al cierre de la fase.

Con esto, las **10 fases de MercadoInsight quedan definidas** y la siguiente etapa natural ya no sería diseñar otra fase, sino comenzar la implementación concreta desde **Fase 1.1 en adelante**, ejecutando los TODO de manera incremental.
