# Model & Version Management (Fase 6.22)

Gestión del ciclo de vida, linaje, versionado y reproducibilidad de modelos, datasets, taxonomías y diccionarios semánticos en MercadoInsight.

---

## 1. Entidades de Versionado

El sistema asegura trazabilidad completa mediante cuatro contratos de versionado:

1. **`ModelVersion` (`knowledge.model_versions`)**:
   - `id`: UUID único del modelo.
   - `name`: Identificador de arquitectura (ej. `classifier_sgd`, `embeddings_logreg`).
   - `version`: Versión semántica o secuencial del modelo (ej. `v1.0`, `v2.1`).
   - `kind`: Tipo funcional (`classifier`, `ner`, `embeddings`).
   - `status`: Estado del ciclo de vida (`draft`/`development`, `staging`, `production`, `archived`).
   - `artifact_uri`: Ubicación inmutable del archivo serializado en MinIO/S3 (ej. `s3://models/classifier_v2.1.joblib`).
   - `parameters`: Hiperparámetros, identificador del Gold Dataset (`dataset_version_id`) y fecha de entrenamiento (`trained_at`).
   - `metrics`: Métricas de evaluación (F1 macro, accuracy, matriz de confusión, métricas por clase).

2. **`DatasetVersion` (`knowledge.dataset_versions`)**:
   - Manifiesto con recuento de registros, distribución de etiquetas y versión de taxonomía utilizada para el etiquetado.

3. **`TaxonomyVersion` (`TaxonomyVersion("taxonomy-YYYY.M")`)**:
   - Contrato inmutable que identifica la estructura jerárquica de 3 niveles (`Category` -> `Subcategory` -> `Concept`).

4. **`DictionaryVersion` (`DictionaryVersion("dictionary-YYYY.M")`)**:
   - Contrato inmutable que identifica el vocabulario de sinónimos, abreviaturas y conceptos de producto.

---

## 2. Ciclo de Vida y Transiciones de Estado

Las transiciones de estado están gobernadas por `validate_model_transition`:

```
               ┌──────────┐
               │  DRAFT   │
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐
         ┌────►│ STAGING  │◄─────┐
         │     └────┬─────┘      │ (Rollback)
         │          │            │
         │          ▼            │
         │     ┌──────────┐      │
         │     │PRODUCTION├──────┘
         │     └────┬─────┘
         │          │
         ▼          ▼
       ┌──────────────┐
       │   ARCHIVED   │
       └──────────────┘
```

- **Invariante de Producción**: Sólo puede existir **un modelo activo** en estado `production` por cada `kind`.
- **Promoción a Producción**: Al promover un modelo de `staging` a `production`, el modelo actualmente productivo es demotado automáticamente a `staging`.
- **Rollback**: En caso de degradación o regresión en producción, la operación de rollback demota el modelo productivo a `staging` y restaura el modelo de `staging` más reciente a `production`.

---

## 3. Linaje y Procedencia (`ModelLineage`)

El linaje reconstruye la historia completa de un modelo:
- Dataset Gold exacto con el que fue entrenado (`dataset_version_id`, `record_count`).
- Hiperparámetros del optimizador y pesos de clases.
- Métricas de prueba en datos ciegos.
- Conteo de inferencias y clasificaciones generadas en la tabla `knowledge.classifications`.

---

## 4. Endpoints REST

- `GET /api/v1/ai/models`: Listado de modelos y datasets.
- `POST /api/v1/ai/models/{model_id}/promote`: Promueve un modelo a `staging`, `production` o `archived`.
- `POST /api/v1/ai/models/rollback`: Ejecuta rollback al modelo previo en producción.
- `GET /api/v1/ai/models/{model_id}/lineage`: Consulta el linaje completo del modelo.
