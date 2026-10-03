# Especificación y Consumo de la API — MercadoInsight

Este documento detalla la interfaz de programación de aplicaciones (API) REST de **MercadoInsight**, sus convenciones de diseño, esquemas de autenticación, paginación, filtros y endpoints.

---

## 1. Documentación Interactiva

FastAPI genera documentación automática compatible con OpenAPI 3.1:
- **Swagger UI**: `/api/docs` — Interfaz interactiva para probar endpoints y visualizar esquemas.
- **ReDoc**: `/api/redoc` — Documentación detallada y legible orientada a consumo y desarrollo.
- **OpenAPI JSON Schema**: `/api/openapi.json` — Definición cruda de la API para generación de clientes tipados.

> [!IMPORTANT]
> En entornos de producción (`ENVIRONMENT=production`), la UI interactiva de Swagger puede desactivarse o limitarse mediante control de acceso por IP en NGINX para evitar exposición innecesaria de la superficie de ataque.

---

## 2. Autenticación y Autorización

La API implementa **JSON Web Tokens (JWT)** bajo el estándar RFC 7519:

### 2.1 Flujo de Autenticación
1. **Obtención de Token**:
   `POST /api/v1/auth/login`
   ```json
   {
     "username": "analista@mercadoinsight.cl",
     "password": "Password123!"
   }
   ```
   **Respuesta (`200 OK`)**:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer",
     "expires_in": 3600
   }
   ```
2. **Uso de Token en Peticiones Protegidas**:
   Cabecera HTTP requerida:
   ```http
   Authorization: Bearer <access_token>
   ```
3. **Renovación de Token**:
   `POST /api/v1/auth/refresh` enviando el `refresh_token`.

---

## 3. Manejo Canónico de Errores

Las respuestas de error siguen el estándar de problemas HTTP con estructura JSON uniforme:

```json
{
  "error": "RESOURCE_NOT_FOUND",
  "detail": "No se encontró la licitación con código 1000-01-LR26.",
  "status_code": 404,
  "timestamp": "2026-09-22T12:00:00Z",
  "request_id": "req-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```

Códigos de estado HTTP principales:
- `200 OK`: Petición exitosa.
- `201 Created`: Recurso creado exitosamente.
- `202 Accepted`: Tarea asíncrona encolada en Celery.
- `400 Bad Request`: Parámetros o cuerpo de la petición inválidos.
- `401 Unauthorized`: Token JWT ausente, expirado o inválido.
- `403 Forbidden`: Permisos insuficientes (control de roles RBAC).
- `404 Not Found`: Recurso inexistente.
- `422 Unprocessable Entity`: Error de validación en esquema Pydantic.
- `429 Too Many Requests`: Exceso de rate limit.
- `500 Internal Server Error`: Excepción no controlada (sin fuga de trazas internas).

---

## 4. Paginación y Filtrado

Para listados masivos (licitaciones, adjudicaciones, proveedores):

### Parámetros Estándar de Query
- `page`: Número de página (1-indexado, por defecto `1`).
- `page_size`: Elementos por página (por defecto `20`, máximo `100`).
- `sort_by`: Campo para ordenamiento (ejemplo: `fecha_cierre`, `monto_total`).
- `order`: Dirección del orden (`asc` o `desc`).
- `search`: Término de búsqueda textual.
- `region_code`: Filtro geográfico (código regional de Chile).
- `estado`: Estado de la licitación (`publicada`, `cerrada`, `adjudicada`, `desierta`).

### Respuesta Paginada
```json
{
  "items": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1420,
    "total_pages": 71,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## 5. Endpoints Principales del Sistema

### 5.1 Autenticación y Usuarios (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Autenticación con credenciales.
- `POST /api/v1/auth/refresh`: Renovación de JWT.
- `GET /api/v1/auth/me`: Perfil del usuario en sesión.

### 5.2 Licitaciones y Analítica (`/api/v1/adjudicaciones`, `/api/v1/licitaciones`)
- `GET /api/v1/adjudicaciones/summary`: Resumen ejecutivo de gasto y adjudicaciones.
- `GET /api/v1/adjudicaciones/history/{external_id}`: Historial temporal de adjudicaciones por entidad.
- `GET /api/v1/licitaciones`: Explorador de licitaciones con filtros facetados.

### 5.3 Procesamiento de Lenguaje Natural (`/api/v1/nlp`)
- `POST /api/v1/nlp/classify`: Clasificación léxica y semántica de un texto o licitación.
- `POST /api/v1/nlp/extract-entities`: Extracción NER de montos, organismos e ítems.
- `POST /api/v1/nlp/hybrid-search`: Búsqueda híbrida (FTS + vector) con ponderación RRF.

### 5.4 Asistente Conversacional RAG (`/api/v1/chat`)
- `POST /api/v1/chat/conversations`: Creación de nueva sesión conversacional.
- `POST /api/v1/chat/conversations/{id}/messages`: Envío de mensaje del usuario.
- `GET /api/v1/chat/conversations/{id}/messages/stream`: Consumo de respuesta en streaming vía **Server-Sent Events (SSE)**.
- `POST /api/v1/chat/feedback`: Envío de evaluación de fidelidad (thumbs up/down).

### 5.5 Salud y Telemetría (`/api/v1/system`, `/health`, `/metrics`)
- `GET /health/live`: Liveness probe para orquestadores.
- `GET /health/ready`: Readiness probe verificando PostgreSQL, Redis y MinIO.
- `GET /metrics`: Métricas de Prometheus para scraping.
- `GET /api/v1/system/status`: Diagnóstico operacional detallado.
