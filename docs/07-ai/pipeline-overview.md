# Pipeline Overview — NLP & Knowledge Layer (Fase 6)

Guía y especificación integral del pipeline de procesamiento de lenguaje natural (NLP) e inteligencia de mercado en MercadoInsight.

---

## 1. Visión General del Pipeline

El pipeline transforma licitaciones en documentos analíticos enriquecidos mediante un flujo determinista, auditable y desacoplado:

```
                  ┌───────────────────────────────┐
                  │ Licitación Raw / API Externa  │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                     [1] Consolidación Documento
                                  │
                                  ▼
                     [2] Preprocessing Lingüístico
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
[3] Motor de Reglas      [4] Embeddings Densos   [5] Clasif. Supervisada
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                   [6] Fusión Híbrida (HybridDecision)
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
[7] Entidades (NER)                             [8] Productos y Atributos
         │                                                 │
         └────────────────────────┬────────────────────────┘
                                  │
                                  ▼
                    [9] Relevancia de Mercado
                                  │
                                  ▼
               [10] Confidence Scoring & Human Review
                                  │
                                  ▼
               [11] Observabilidad, Métricas y Drift
```

---

## 2. Etapas Detalladas del Pipeline

### [1] Consolidación de Documentos (`app.nlp.document`)
- Consolida campos textuales (`nombre`, `descripcion`) en `TenderDocument` con `DocumentChunk` y hash criptográfico SHA-256 (`content_hash`) para asegurar idempotencia.

### [2] Preprocesamiento Lingüístico (`app.nlp.preprocessing`)
- Normalización léxica (minúsculas, remoción de tildes, limpieza de caracteres especiales).
- Tokenización y filtrado de stopwords en español optimizado para contratación pública chilena.

### [3] Motor de Reglas (`app.nlp.rules`)
- Evaluación determinista basada en el diccionario semántico de dominio (`app.nlp.dictionary`) y la taxonomía (`app.nlp.taxonomy`).
- Resolución de sinónimos, abreviaturas y términos clave para geriatría, discapacidad y ayudas técnicas.

### [4] Generación de Embeddings Densos (`app.ml.embeddings`)
- Vectorización multilingüe (`paraphrase-multilingual-MiniLM-L12-v2` o equivalente) produciendo vectores normalizados L2.
- Indexación vectorial en PostgreSQL mediante la extensión `pgvector` con índices HNSW.

### [5] Búsqueda y Clasificación Semántica (`app.nlp.semantic`, `app.services.nlp.semantic_search`)
- Comparación contra vectores representativos de categorías y conceptos mediante similitud coseno.
- Búsqueda híbrida mediante Reciprocal Rank Fusion (RRF) combinando Full-Text Search y búsqueda vectorial.

### [6] Fusión Híbrida (`app.nlp.classification`, `app.services.nlp.classification`)
- Resolución ponderada de señales (`rule`, `semantic`, `supervised`).
- Si las reglas o semántica coinciden, se consolida la predicción con alta confianza; si discrepan, se genera señal de conflicto.

### [7] Extracción de Entidades Nombradas - NER (`app.nlp.entities`, `app.services.nlp.entities`)
- Extracción de cantidades, unidades de medida, fechas límite, montos monetarios, marcas, modelos y organismos contratantes.

### [8] Extracción de Productos y Atributos (`app.nlp.product_*`, `app.services.nlp.products`)
- Identificación de productos de interés a nivel de ítem.
- Extracción de atributos técnicos: dimensiones, peso soportado, capacidad, materiales y características técnicas.

### [9] Relevancia de Mercado (`app.nlp.market_relevance`, `app.services.nlp.relevance`)
- Evaluación bidimensional: pertinencia temática al nicho de negocio vs. pertinencia comercial temporal (fecha de cierre de la licitación).
- Asignación de tiers: `ALTA`, `MEDIA`, `BAJA`.

### [10] Confidence Scoring & Human-in-the-Loop (`app.nlp.confidence`, `app.nlp.human_review`)
- Asignación de `confidence_score` en $[0.0, 1.0]$.
- Criterios de escalación a cola de revisión humana:
  - Confianza baja ($< 0.70$).
  - Conflicto entre reglas y modelo supervisado.
  - Categoría no asignada o relevancia en el límite.
- Registro auditable de decisiones humanas y retroalimentación al Gold Dataset.

### [11] Infraestructura Asíncrona, Observabilidad y MLOps (`app.worker`, `app.nlp.observability`, `app.nlp.mlops`)
- Tareas Celery (`process_nlp_job`, `process_nlp_batch`) desacopladas vía Redis.
- Métricas Prometheus (`market_insight_nlp_*`), tableros en Grafana y detección continua de Data Drift vía divergencia Kullback-Leibler.
- Versionado inmutable (`ModelVersion`, `DatasetVersion`, `TaxonomyVersion`, `DictionaryVersion`) con rollback automatizado.

---

## 3. Endpoints REST de Consulta

Todas las capacidades del pipeline están expuestas bajo `/api/v1/ai`:
- `POST /api/v1/ai/classify`: Clasificación híbrida en tiempo real.
- `POST /api/v1/ai/search`: Búsqueda vectorial semántica.
- `GET /api/v1/ai/similar/{id}`: Búsqueda de licitaciones similares.
- `POST /api/v1/ai/entities`: Extracción de entidades nombradas.
- `POST /api/v1/ai/products`: Extracción de productos y atributos.
- `GET /api/v1/ai/categories`: Taxonomía jerárquica de 3 niveles.
- `POST /api/v1/ai/relevance`: Cálculo de relevancia de mercado.
- `GET /api/v1/ai/reviews`: Cola priorizada de revisión humana.
- `POST /api/v1/ai/jobs`: Procesamiento asíncrono en segundo plano.
- `POST /api/v1/ai/models/{id}/promote`: Promoción de modelos.
- `POST /api/v1/ai/models/rollback`: Rollback automático a versión previa.
- `POST /api/v1/ai/models/retrain`: Reentrenamiento reproducible y validación de regresión.
