# Gestión de Configuración — MercadoInsight

Este documento establece las políticas, taxonomía y herramientas de validación de configuración de **MercadoInsight** siguiendo el principio de **Configuración en el Entorno** (The Twelve-Factor App).

---

## 1. Principios de Configuración

1. **Separación Estricta de Código y Configuración**:
   - Todo parámetro que varíe entre despliegues (`development`, `testing`, `staging`, `production`) se almacena exclusivamente en variables de entorno.
   - Ningún valor de configuración dinámico, URL externa, cadena de conexión o credencial debe estar hardcodeado en el código fuente de Python, TypeScript, SQL o Dockerfiles.
2. **Validación Tipada en Tiempo de Inicialización**:
   - El backend utiliza `pydantic-settings` para validar nombres, tipos y restricciones de variables en cuanto arranca el proceso. Si una variable obligatoria falta o tiene un tipo incorrecto, la aplicación aborta con un mensaje de diagnóstico inmediato.
3. **Plantillas Versionadas y Secretos Ignorados**:
   - El repositorio solo contiene plantillas de ejemplo (`.env.example`, `.env.test.example`, `.env.staging.example`, `.env.prod.example`).
   - Los archivos `.env` y `.env.*` reales están estrictamente ignorados en `.gitignore` y `.dockerignore`.

---

## 2. Taxonomía Completa de Variables de Entorno

### 2.1 Identificación y Núcleo de la Aplicación

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `APP_ENV` / `ENVIRONMENT` | string | `development` | Todos | Nombre del entorno activo (`development`, `test`, `staging`, `production`). |
| `APP_NAME` | string | `MercadoInsight API` | Todos | Nombre descriptivo del servicio en logs y telemetría. |
| `APP_VERSION` | string | `0.1.0` | Todos | Versión semántica del software. |
| `API_V1_PREFIX` | string | `/api/v1` | Todos | Prefijo canónico de endpoints REST v1. |
| `DEBUG` | boolean | `false` | Dev / Test | Activa modo de depuración interactivo (siempre `false` en staging y prod). |

### 2.2 Seguridad y Autenticación

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `SECRET_KEY` | string | `change-me...` | Todos | Clave simétrica de 256 bits para firma de tokens JWT. **Obligatoria y validada en staging y prod**. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| integer | `60` | Todos | Tiempo de vida de los tokens de sesión. |
| `BACKEND_CORS_ORIGINS` | string | `http://localhost:5173` | Todos | Lista separada por comas de orígenes permitidos para peticiones CORS. |
| `PUBLIC_BASE_URL` | string | N/A | Staging / Prod | Dominio público canónico accesible por NGINX (ej. `https://mercadoinsight.cl`). |
| `METRICS_AUTH_TOKEN` | string | `None` | Todos | Token secreto requerido para scraping autenticado de `/metrics`. |
| `ALERT_WEBHOOK_TOKEN` | string | `None` | Staging / Prod | Token Bearer compartido entre Alertmanager y el webhook de la API. |
| `RATE_LIMIT_ENABLED` | boolean | `false` | Todos | Activa o desactiva la protección contra saturación por IP. |
| `RATE_LIMIT_REQUESTS` | integer | `100` | Staging / Prod | Límite de peticiones por ventana de tiempo. |
| `RATE_LIMIT_WINDOW_SECONDS` | integer | `60` | Staging / Prod | Tamaño de la ventana de evaluación de rate limiting. |

### 2.3 Base de Datos PostgreSQL (OLTP + pgvector)

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `POSTGRES_HOST` | string | `postgres` | Dev / Test | Host del servidor PostgreSQL. |
| `POSTGRES_PORT` | integer | `5432` | Dev / Test | Puerto de escucha de PostgreSQL. |
| `POSTGRES_DB` | string | `market_insight` | Todos | Nombre de la base de datos principal. |
| `POSTGRES_USER` | string | `market_insight` | Dev / Test | Usuario root / superusuario local. |
| `POSTGRES_PASSWORD` | string | `market_insight_dev` | Staging / Prod | Clave maestra del contenedor PostgreSQL. |
| `MARKET_INSIGHT_ADMIN_PASSWORD` | string | N/A | Staging / Prod | Clave para el rol de migraciones y DDL (`market_insight_admin`). |
| `MARKET_INSIGHT_APP_PASSWORD` | string | N/A | Staging / Prod | Clave para el rol de la aplicación API (`market_insight_app`). |
| `MARKET_INSIGHT_READONLY_PASSWORD` | string | N/A | Staging / Prod | Clave para el rol de lectura y reportes (`market_insight_readonly`). |
| `DATABASE_URL` | string | `postgresql+psycopg...` | Todos | Cadena de conexión SQLAlchemy / Psycopg3 utilizada por FastAPI y Alembic. |

### 2.4 Cache, Colas y Mensajería (Redis)

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `REDIS_HOST` | string | `redis` | Dev / Test | Host de conexión a Redis. |
| `REDIS_PORT` | integer | `6379` | Dev / Test | Puerto de Redis. |
| `REDIS_PASSWORD` | string | N/A | Todos | Contraseña de autenticación de Redis (parámetro `--requirepass`). |
| `REDIS_URL` | string | `redis://...` | Todos | URI completa con credenciales para conexión de FastAPI y Celery. |

### 2.5 Object Storage S3 (MinIO)

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `MINIO_ENDPOINT` | string | `minio:9000` | Todos | Host y puerto del servicio S3 compatible. |
| `MINIO_ROOT_USER` | string | `marketinsight` | Staging / Prod | Usuario administrador de MinIO. |
| `MINIO_ROOT_PASSWORD` | string | N/A | Staging / Prod | Clave de administrador de MinIO. |
| `MINIO_ACCESS_KEY` | string | `marketinsight` | Todos | Access key S3 para la aplicación. |
| `MINIO_SECRET_KEY` | string | N/A | Todos | Secret key S3 para la aplicación. |
| `MINIO_BUCKET_DOCUMENTS` | string | `documents` | Todos | Bucket para bases de licitaciones y archivos adjuntos. |
| `MINIO_BUCKET_ML_MODELS` | string | `ml-models` | Todos | Bucket para artefactos y modelos de Machine Learning / NLP. |

### 2.6 Integraciones Externas (ChileCompra y LLM)

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `CHILECOMPRA_API_URL` | string | `https://api.mercadopublico.cl...` | Todos | URL base del API de Mercado Público. |
| `CHILECOMPRA_API_KEY` | string | N/A | Todos | Ticket / API Key provisto por ChileCompra para consultas. |
| `CHILECOMPRA_TIMEOUT` | float | `30.0` | Todos | Timeout de red en segundos para llamadas al API externa. |
| `LLM_PROVIDER` | string | `local` | Todos | Proveedor LLM activo (`local`, `openai`, `anthropic`). |
| `LLM_API_KEY` | string | `None` | Staging / Prod | Token de autenticación del proveedor LLM seleccionado. |
| `LLM_MODEL_NAME` | string | `claude-3-5-sonnet...` | Todos | Identificador del modelo para generación y RAG. |

### 2.7 Observabilidad y Monitoreo

| Variable | Tipo | Default | Entornos | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `LOG_LEVEL` | string | `INFO` | Todos | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FORMAT` | string | `auto` | Todos | Formato de logs (`auto`, `console`, `json`). |
| `SENTRY_DSN` | string | `None` | Staging / Prod | DSN del proyecto en Sentry para tracking de errores no controlados. |
| `SENTRY_ENVIRONMENT` | string | `None` | Staging / Prod | Etiqueta de entorno reportada a Sentry. |
| `OTEL_ENABLED` | boolean | `true` | Staging / Prod | Activa la instrumentación de trazas distribuidas con OpenTelemetry. |
| `OTEL_EXPORTER_OTLP_ENDPOINT`| string | `None` | Staging / Prod | Endpoint gRPC o HTTP del OTel Collector. |
| `GRAFANA_ADMIN_PASSWORD` | string | N/A | Staging / Prod | Clave de administrador inicial para Grafana. |

---

## 3. Matriz de Archivos de Plantilla

El proyecto provee cuatro plantillas diseñadas según el nivel de aislamiento y criticidad:

1. [`.env.example`](file:///c:/Users/artut/market-insight/.env.example): Plantilla integral para desarrollo local. Incluye valores por defecto no confidenciales que permiten levantar el stack con `make dev-up` inmediatamente.
2. [`.env.test.example`](file:///c:/Users/artut/market-insight/.env.test.example): Plantilla optimizada para testing y CI. Desactiva rate limits y telemetría innecesaria, y apunta a bases de datos aisladas.
3. [`.env.staging.example`](file:///c:/Users/artut/market-insight/.env.staging.example): Plantilla estricta para pre-producción. Requiere generar contraseñas seguras y define variables para Sentry y Alertmanager.
4. [`.env.prod.example`](file:///c:/Users/artut/market-insight/.env.prod.example): Plantilla estricta para producción. Sin valores por defecto; Docker Compose aborta (`:?variable is required`) si alguna clave requerida se omite.

---

## 4. Validación Automatizada de Configuración

Para prevenir errores de despliegue antes de tocar los contenedores, se incluye la herramienta de validación CLI:

```bash
# Validar plantilla de desarrollo
python infrastructure/scripts/validate-env.py --env development --file .env.example

# Validar archivo de staging antes del deploy
python infrastructure/scripts/validate-env.py --env staging --file .env.staging

# Validar archivo de producción con detección de placeholders inseguros
python infrastructure/scripts/validate-env.py --env production --file .env.prod --check-placeholders
```

Esta validación está integrada en el pipeline de CI/CD y en el target `make validate-env`.
