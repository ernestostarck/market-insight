# Documentación de la API REST — MercadoInsight

Este documento describe la especificación, contratos, mecanismos de autenticación y consumo de la **API REST de MercadoInsight** (`apps/backend`), construida sobre **FastAPI** y expuesta bajo el estándar **OpenAPI 3.1**.

---

## 1. Documentación Interactiva y OpenAPI

FastAPI autogenera la especificación completa a partir de los esquemas Pydantic y las anotaciones de tipos:

| Recurso | URL | Propósito |
| :--- | :--- | :--- |
| **Swagger UI** | `/api/docs` | Consola interactiva para explorar endpoints, schemas y ejecutar peticiones de prueba con token JWT. |
| **ReDoc** | `/api/redoc` | Documentación técnica estructurada de dos columnas, optimizada para desarrolladores de integraciones. |
| **OpenAPI Schema** | `/api/openapi.json` | Definición en formato JSON estándar para generación de SDKs clientes (TypeScript, Python, Go). |

### 1.1 Protección de Swagger en Producción
En entornos de producción (`ENVIRONMENT=production`):
- Se puede desactivar completamente definiendo `openapi_url=None`, `docs_url=None`, `redoc_url=None` en `settings.py`.
- O bien restringir el acceso a `/api/docs` y `/api/redoc` a través de NGINX permitiendo únicamente IPs de la VPN administrativa o subred de infraestructura.

---

## 2. Autenticación y Autorización

La API implementa **JSON Web Tokens (JWT)** con algoritmo HS256:

### 2.1 Obtención de Credenciales
`POST /api/v1/auth/login`
```json
{
  "username": "usuario@mercadoinsight.cl",
  "password": "PasswordSegura123!"
}
```

**Respuesta Exitosa (`200 OK`)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 2.2 Inyección de Token
En todas las peticiones a endpoints protegidos, se debe incluir la cabecera HTTP:
```http
Authorization: Bearer <access_token>
```

---

## 3. Manejo Estándar de Errores (RFC 7807)

Todas las respuestas de error retornan un objeto JSON uniforme con identificador único de rastreo:

```json
{
  "error": "VALIDATION_ERROR",
  "detail": "El código de licitación debe tener el formato 1234-56-XX26.",
  "status_code": 422,
  "timestamp": "2026-09-22T12:00:00Z",
  "request_id": "req-7b89d4e5-9a8b-4c7d-8e9f-0a1b2c3d4e5f"
}
```

Códigos HTTP representativos:
- `200 OK`: Operación exitosa.
- `201 Created`: Recurso creado.
- `202 Accepted`: Proceso encolado asíncronamente en Celery.
- `400 Bad Request`: Petición malformada.
- `401 Unauthorized`: Token no provisto o inválido.
- `403 Forbidden`: Privilegios insuficientes para la acción.
- `404 Not Found`: Entidad no encontrada en el sistema.
- `422 Unprocessable Entity`: Error de validación en datos enviados.
- `429 Too Many Requests`: Límite de tasa excedido.
- `500 Internal Server Error`: Fallo interno sin revelación de datos sensibles.

---

## 4. Convenciones de Paginación y Filtrado

Para colecciones de datos masivos:
- **`page`**: Número de página deseada (entero $\ge 1$, por defecto `1`).
- **`page_size`**: Cantidad de registros por página (entero entre `1` y `100`, por defecto `20`).
- **`sort_by`**: Nombre de la columna de ordenación (ej. `fecha_cierre`, `monto_estimado`).
- **`order`**: Sentido del orden (`asc` o `desc`).
- **Filtros Facetados**: Parámetros opcionales (`region_code`, `estado`, `organismo_rut`, `proveedor_rut`, `min_monto`, `max_monto`).

---

## 5. Endpoints de Inteligencia Artificial & Conversación

### 5.1 Búsqueda Híbrida (`/api/v1/nlp/hybrid-search`)
`POST /api/v1/nlp/hybrid-search`
```json
{
  "query": "grúas de transferencia para pacientes geriátricos",
  "limit": 10,
  "alpha": 0.5,
  "filters": {
    "region_code": "13",
    "estado": "publicada"
  }
}
```
Combina búsqueda semántica `pgvector` y búsqueda de texto completo ponderadas por Reciprocal Rank Fusion (RRF).

### 5.2 Streaming Conversacional SSE (`/api/v1/chat/conversations/{id}/messages/stream`)
Las respuestas del Asistente RAG se envían mediante **Server-Sent Events** (`text/event-stream`):
```text
event: sources
data: [{"id": "1058-12-LR26", "title": "Sillas de Ruedas Senama", "score": 0.94}]

event: token
data: {"text": "Durante "}

event: token
data: {"text": "el año 2024, "}

event: token
data: {"text": "Senama adjudicó un total de $45.000.000 CLP..."}

event: done
data: {"tokens_input": 520, "tokens_output": 84, "cost_usd": 0.0018, "grounding_score": 0.98}
```

---

## 6. Rate Limiting

La API implementa dos niveles de limitación:
1. **Nivel NGINX**:
   - `10 req/s` por IP con burst de 20 para endpoints generales.
   - `5 req/m` por IP para `/api/v1/auth/login` para mitigar ataques de fuerza bruta.
2. **Nivel Aplicación (SlowAPI)**:
   - Límites específicos por usuario autenticado sobre endpoints costosos de IA (máximo 15 preguntas RAG por hora en planes estándar).
