# Arquitectura del Backend — FastAPI & Worker

Este documento describe la arquitectura interna del backend de **MercadoInsight** (`apps/backend`), cubriendo la estructura de directorios, el framework FastAPI, la capa de servicios, repositorios, tareas en segundo plano con Celery y gestión del ciclo de vida.

---

## 1. Estructura de Módulos

El backend está organizado dentro de `apps/backend/app/` separando claramente responsabilidades:

```text
apps/backend/app/
├── ai/                     # Motor RAG, clasificador, cost tracker, Text-to-SQL
├── api/                    # Enrutadores FastAPI
│   └── v1/
│       └── endpoints/      # auth, ai, chat, etl, monitoring, system, etc.
├── core/                   # Configuración (settings), seguridad, telemetría, sentry
├── db/                     # Sesiones SQLAlchemy y engine
├── etl/                    # Ingesta, validación, transformación y carga
├── models/                 # Modelos declarativos SQLAlchemy (core, ai, dw, user)
├── monitoring/             # Colectores y métricas Prometheus de negocio
├── nlp/                    # Preprocesamiento de texto, embeddings, reglas, taxonomía
├── repositories/           # Repositorios concretos y contratos
├── schemas/                # Esquemas Pydantic v2 (DTOs request/response)
├── services/               # Lógica de aplicación y orquestadores
└── worker/                 # Celery workers y tareas asíncronas
```

---

## 2. Framework FastAPI y Pipeline de Peticiones

Cada solicitud HTTP entrante atraviesa el siguiente ciclo:

1. **NGINX Reverse Proxy**: Terminación TLS, rate limiting por zona IP y cabeceras de proxy (`X-Forwarded-For`, `X-Forwarded-Proto`).
2. **Middleware de Telemetría y Contexto**: Inyección de `X-Request-ID` único, medición de latencia para Prometheus (`market_insight_http_requests_total`) y captura de contexto de usuario.
3. **Middleware de Seguridad**: CORS restringido a orígenes autorizados, bloqueo de credenciales inseguras y filtros de cabeceras.
4. **Enrutamiento y Validación**: Enrutador FastAPI (`APIRouter`) con prefijo `/api/v1` y parseo canónico mediante schemas Pydantic v2.
5. **Inyección de Dependencias (`Depends`)**:
   - `get_db`: Sesión de base de datos SQLAlchemy con commit/rollback transaccional garantizado.
   - `get_current_user`: Validación de token JWT Bearer, extracción de claims y verificación de estado activo.
   - Repositorios y Servicios instanciados según necesidad.

---

## 3. Patrón Repositorio y Acceso a Datos

El acceso a PostgreSQL y pgvector se realiza mediante repositorios tipados:
- **`SQLAlchemyRepository`**: Provee operaciones CRUD estándar y consultas optimizadas mediante SQLAlchemy 2 select statements.
- **`HybridSearchRepository`**: Coordina la búsqueda combinada entre `pg_trgm` / `tsvector` (Full-Text Search en español) y búsqueda vectorial con `pgvector` mediante Reciprocal Rank Fusion (RRF).
- **`VectorSearchRepository`**: Ejecución de búsquedas vectoriales utilizando operadores de distancia coseno `<=>` contra índices HNSW en el schema `knowledge`.

---

## 4. Procesamiento Asíncrono con Celery & Redis

Las operaciones computacionalmente intensivas o que interactúan con APIs externas no bloquean los hilos HTTP:

```text
FastAPI Request
      │
      ▼
Celery Task Enqueue  ───>  Redis Queue (Broker)
      │                           │
  HTTP 202 Accepted               ▼
                           Celery Worker Process
                           ├── Ingesta ETL de ChileCompra
                           ├── Generación de Embeddings
                           ├── Clasificación NLP y Reglas
                           └── Sincronizaciones Masivas
```

- **Colas Dedicadas**: Colas separadas en Redis para `default`, `etl`, `nlp` y `ai`.
- **Idempotencia**: Claves de deduplicación calculadas mediante hash SHA-256 de parámetros.
- **Backoff Exponencial**: Reintentos automáticos ante caídas transitorias de red o rate limits de APIs de terceros.

---

## 5. Pruebas y Validación

La capa backend cuenta con cobertura exhaustiva mediante `pytest`:
- **Pruebas Unitarias**: Evaluación aislada de servicios, validadores Pydantic y reglas NLP sin base de datos.
- **Pruebas de Integración**: Pruebas con PostgreSQL de testing y endpoints FastAPI utilizando `TestClient` y `pytest-asyncio`.
