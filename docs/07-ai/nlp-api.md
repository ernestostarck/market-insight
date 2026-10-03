# NLP & AI REST API (Fase 6.21)

La **API REST de IA y NLP** expone los servicios inteligentes del sistema bajo el prefijo unificado `/api/v1/ai`. Proporciona acceso sincrónico y asíncrono a la clasificación híbrida, búsqueda semántica vectorial, extracción de entidades y atributos técnicos, taxonomía, evaluación de relevancia de mercado, auditoría HITL (Human-in-the-Loop) y control de modelos.

---

## 1. Principios de Diseño y Arquitectura

1. **Autenticación Unificada**: Todos los endpoints requieren autenticación mediante JWT Bearer token vía `Depends(get_current_user)` configurado a nivel de router en `app/api/v1/router.py`.
2. **Esquemas Pydantic Fuertes**: Validación estricta y serialización mediante modelos en `app/schemas/nlp.py`.
3. **Inyección de Dependencias**: Los controladores en `app/api/v1/endpoints/ai.py` delegan la lógica en los servicios de dominio correspondientes (`app/services/nlp/`) inyectados mediante `app/db/dependencies.py`.
4. **Documentación OpenAPI Automática**: Cada endpoint incluye descripciones, modelos de solicitud/respuesta y códigos de error estándar en Swagger UI (`/docs`) y ReDoc (`/redoc`).

---

## 2. Catálogo de los 11 Endpoints

### 1. Clasificación Híbrida (`POST /api/v1/ai/classify`)
- **Descripción**: Ejecuta la clasificación combinando reglas determinísticas, embeddings vectoriales y modelo supervisado con cálculo de relevancia.
- **Request (`ClassifyRequest`)**:
  ```json
  {
    "text": "Compra de 500 cajas de paracetamol para hospital",
    "title": "Adquisición de fármacos",
    "description": "Hospital Regional",
    "items": ["Paracetamol 500mg"],
    "still_open": true
  }
  ```
- **Response (`ClassifyResponse`)**: `200 OK`
  ```json
  {
    "category_code": "SALUD",
    "subcategory_code": "MEDICAMENTOS",
    "confidence_score": 0.92,
    "winning_method": "supervised",
    "rule_score": 0.85,
    "similarity_score": 0.88,
    "model_score": 0.95,
    "relevance_score": 0.90,
    "relevance_tier": "alta",
    "explanation": {
      "winning_method": "supervised",
      "model_version": "v2.1"
    }
  }
  ```

---

### 2. Historial de Clasificaciones (`GET /api/v1/ai/classifications`)
- **Query Params**:
  - `licitacion_id` (opcional): Filtrar por ID de licitación.
  - `category_id` (opcional): Filtrar por ID de categoría.
  - `limit` (default: 50, max: 200), `offset` (default: 0).
- **Response (`ClassificationListResponse`)**: `200 OK`
  ```json
  {
    "total": 1,
    "items": [
      {
        "id": "7b8f9e10-1234-4567-89ab-cdef01234567",
        "licitacion_id": 42,
        "category_id": 1,
        "subcategory_id": 2,
        "taxonomy_version": "taxonomy-2026.2",
        "confidence_score": 0.88,
        "relevance_tier": "alta",
        "created_at": "2026-09-20T12:00:00Z"
      }
    ]
  }
  ```

---

### 3. Búsqueda Semántica Vectorial (`POST /api/v1/ai/search`)
- **Descripción**: Búsqueda por similitud semántica utilizando vectores en `pgvector`.
- **Request (`SemanticSearchRequest`)**:
  ```json
  {
    "query": "insumos médicos de urgencia",
    "top_k": 10,
    "min_similarity": 0.65,
    "category_code": "SALUD"
  }
  ```
- **Response (`SemanticSearchResponse`)**: `200 OK`
  ```json
  {
    "query": "insumos médicos de urgencia",
    "total": 1,
    "items": [
      {
        "licitacion_id": 101,
        "nombre": "Adquisición de insumos médicos",
        "similarity": 0.8912,
        "category_id": 3,
        "subcategory_id": 4
      }
    ]
  }
  ```

---

### 4. Licitaciones Similares (`GET /api/v1/ai/similar/{licitacion_id}`)
- **Path Param**: `licitacion_id: int`
- **Query Params**: `top_k` (1-100), `min_similarity` (0.0-1.0).
- **Response (`SimilarTendersResponse`)**: `200 OK`
  ```json
  {
    "source_licitacion_id": 100,
    "total": 1,
    "items": [
      {
        "licitacion_id": 202,
        "nombre": "Servicio de mantenimiento hospitalario",
        "similarity": 0.9123,
        "category_id": 5,
        "subcategory_id": 6
      }
    ]
  }
  ```

---

### 5. Extracción de Entidades (`POST /api/v1/ai/entities`)
- **Request (`EntityExtractionRequest`)**:
  ```json
  {
    "text": "500 unidades de guantes de látex quirúrgico para Hospital Regional",
    "organismo": "Hospital Regional"
  }
  ```
- **Response (`EntityExtractionResponse`)**: `200 OK`
  ```json
  {
    "total": 1,
    "entities": [
      {
        "entity_type": "CANTIDAD",
        "value": "500 unidades",
        "normalized_value": "500",
        "confidence_score": 0.95,
        "start_offset": 0,
        "end_offset": 12
      }
    ]
  }
  ```

---

### 6. Extracción de Productos y Atributos Técnicos (`POST /api/v1/ai/products`)
- **Request (`ProductExtractionRequest`)**:
  ```json
  {
    "item_nombre": "Paracetamol 500mg comprimidos",
    "item_descripcion": "Caja de 20 tabletas de almidón"
  }
  ```
- **Response (`ProductExtractionResponse`)**: `200 OK`
  ```json
  {
    "concepts": [
      {
        "concept_code": "PARACETAMOL",
        "category_code": "SALUD",
        "subcategory_code": "FARMACOS",
        "matched_term": "paracetamol",
        "start_offset": 0,
        "end_offset": 11
      }
    ],
    "attributes": {
      "materiales": ["almidón"],
      "dimensiones": null,
      "capacidad": "500 mg",
      "caracteristicas_tecnicas": ["comprimidos"]
    }
  }
  ```

---

### 7. Taxonomía y Jerarquía (`GET /api/v1/ai/categories`)
- **Descripción**: Estructura de 3 niveles (`Category` -> `Subcategory` -> `Concept`).
- **Response (`TaxonomyHierarchyResponse`)**: `200 OK`
  ```json
  {
    "version": "taxonomy-2026.2",
    "categories": [
      {
        "code": "SALUD",
        "name": "Salud y Farmacéutica",
        "description": "Sector salud",
        "subcategories": [
          {
            "code": "MEDICAMENTOS",
            "name": "Medicamentos",
            "description": "Fármacos generales",
            "concepts": [
              {
                "code": "ANALGESICOS",
                "name": "Analgésicos",
                "description": "Alivio del dolor"
              }
            ]
          }
        ]
      }
    ]
  }
  ```

---

### 8. Cálculo de Relevancia (`POST /api/v1/ai/relevance`)
- **Request (`RelevanceCalculationRequest`)**:
  ```json
  {
    "rule_score": 0.8,
    "similarity_score": 0.9,
    "model_score": 0.85,
    "still_open": true
  }
  ```
- **Response (`RelevanceCalculationResponse`)**: `200 OK`
  ```json
  {
    "relevance_score": 0.88,
    "relevance_tier": "alta",
    "thematic_score": 0.90,
    "commercial_score": 0.85,
    "explanation": {
      "summary": "Oportunidad comercial alta y temática afín."
    }
  }
  ```

---

### 9. Cola de Revisión Humana HITL (`/api/v1/ai/reviews`)
- **`GET /api/v1/ai/reviews`**: Obtiene licitaciones con baja confianza o señales en conflicto.
- **`POST /api/v1/ai/reviews/{classification_id}/accept`**: Confirma la predicción automática estableciendo confianza 1.0 y auditoría.
- **`POST /api/v1/ai/reviews/{classification_id}/modify`**: Corrige taxonomía o relevancia con validación estricta.
- **`GET /api/v1/ai/reviews/stats`**: Métricas globales de la auditoría humana (tasa de acuerdo, volumen revisado).

---

### 10. Modelos y Datasets Versionados (`GET /api/v1/ai/models`)
- **Descripción**: Lista los clasificadores y datasets registrados en la base de conocimiento (`knowledge.model_versions`, `knowledge.dataset_versions`).
- **Response (`ModelListResponse`)**: `200 OK`

---

### 11. Jobs Asíncronos (`/api/v1/ai/jobs`)
- **`POST /api/v1/ai/jobs`**: Encola una licitación individual para procesamiento en background (`202 Accepted`).
  ```json
  {
    "licitacion_id": 888,
    "text_hash": "a1b2c3d4...",
    "taxonomy_version": "taxonomy-2026.2",
    "dictionary_version": "dictionary-2026.1"
  }
  ```
- **`POST /api/v1/ai/jobs/batch`**: Encola un lote de licitaciones (`202 Accepted`).
- **`GET /api/v1/ai/jobs/{job_id}`**: Consulta el estado de una tarea (`queued`, `running`, `succeeded`, `failed`) consultando Redis primero y PostgreSQL como fallback.

---

## 3. Códigos de Estado y Manejo de Errores

| Código | Significado | Causa común |
|---|---|---|
| `200 OK` | Éxito | Solicitud sincrónica procesada correctamente. |
| `202 Accepted` | Aceptado | Job asíncrono encolado en Redis exitosamente. |
| `400 Bad Request` | Petición inválida | Faltan campos requeridos o error taxonómico en modificación. |
| `401 Unauthorized` | No autenticado | Token JWT ausente o expirado. |
| `404 Not Found` | No encontrado | Job o recurso inexistente en Redis ni en PostgreSQL. |
| `422 Unprocessable` | Validación fallida | Esquema Pydantic no cumple restricciones de tipos o rangos. |
