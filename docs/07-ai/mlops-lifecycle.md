# MLOps & Evaluation Pipeline (Fase 6.23)

Pipeline integral de entrenamiento reproducible, evaluación cuantitativa, validación de regresión y seguimiento de experimentos para modelos NLP en MercadoInsight.

---

## 1. Arquitectura del Ciclo MLOps

El ciclo de vida de los modelos NLP sigue un flujo determinista y auditable:

```
┌─────────────────┐     ┌────────────────────────┐     ┌──────────────────────┐
│  Gold Dataset   │ ──► │  Split Determinista    │ ──► │ Candidatos Modelos   │
│ (DatasetVersion)│     │  (Train / Val / Test)  │     │ (TF-IDF / Embeddings)│
└─────────────────┘     └────────────────────────┘     └──────────┬───────────┘
                                                                  │
                                                                  ▼
┌─────────────────┐     ┌────────────────────────┐     ┌──────────────────────┐
│ MLflow Tracking │ ◄── │  Promoción / Gate      │ ◄── │ Validación Regresión │
│ (Runs/Artifacts)│     │  (PromotionPolicy)     │     │(RegressionValidator) │
└─────────────────┘     └────────────────────────┘     └──────────────────────┘
```

---

## 2. Pipeline de Entrenamiento Reproducible (`ReproducibleTrainingPipeline`)

Ubicación: [`apps/backend/app/nlp/mlops/pipeline.py`](file:///c:/Users/artut/market-insight/apps/backend/app/nlp/mlops/pipeline.py)

### Características:
- **Semilla Fija (`random_state=42`)**: Garantiza reproducibilidad bit a bit de los splits y convergencia de optimizadores (`LogisticRegression`, `SGDClassifier`).
- **Separación de Conjuntos**:
  - `Train`: Ajuste de pesos y vocabularios.
  - `Validation`: Selección del modelo campeón entre candidatos.
  - `Test`: Evaluación final insesgada del candidato ganador.
- **Espacio de Candidatos**:
  1. `tfidf_logreg`: `TfidfVectorizer(ngram_range=(1, 2))` + `LogisticRegression(class_weight="balanced")`.
  2. `tfidf_sgd`: `TfidfVectorizer(ngram_range=(1, 2))` + `SGDClassifier(loss="log_loss", penalty="l2")`.
  3. `embeddings_logreg`: Representaciones semánticas densas (`EmbeddingService`) + `LogisticRegression`.

---

## 3. Métricas de Evaluación (`EvaluationResult`)

Contrato estandarizado de métricas:
- **`accuracy`**: Exactitud global sobre el conjunto de prueba.
- **`precision_macro`**: Precisión no ponderada entre clases.
- **`recall_macro`**: Exhaustividad no ponderada entre clases.
- **`f1_macro`**: Métrica de optimización principal para selección de campeón.
- **`per_class`**: Desglose por categoría (`precision`, `recall`, `f1-score`, `support`).
- **`confusion_matrix`**: Matriz de confusión bidimensional para análisis de error.

---

## 4. Validación de Regresión (`RegressionValidator`)

Previene la degradación en producción comparando el candidato nuevo contra el campeón productivo actual:

```python
validator = RegressionValidator(
    macro_tolerance=0.02,      # Degradación máxima admisible de F1 macro: 2%
    per_class_tolerance=0.05,  # Degradación máxima admisible por clase crítica: 5%
    min_test_accuracy=0.75,    # Accuracy mínima requerida
)
passed, violations = validator.validate(
    candidate_metrics=candidate_metrics,
    baseline_metrics=current_production_metrics,
)
```

Si el modelo degrada alguna categoría por encima de la tolerancia, la validación falla con un reporte detallado de violaciones.

---

## 5. Política de Promoción (`PromotionPolicy`)

Determina si un candidato es apto para avanzar a `staging` o `production`:

```python
policy = PromotionPolicy(
    min_f1_macro=0.70,
    min_accuracy=0.75,
    max_per_class_gap=0.40,
)
decision = policy.evaluate(candidate_metrics, baseline_metrics=prod_metrics)
# decision.allowed: bool
# decision.target_status: "staging" | "production" | "rejected"
# decision.reasons: list[str]
```

---

## 6. Seguimiento de Experimentos (`MLflowTracker`)

Ubicación: [`apps/backend/app/nlp/mlops/tracking.py`](file:///c:/Users/artut/market-insight/apps/backend/app/nlp/mlops/tracking.py)

Provee abstracción transparente sobre MLflow con **soporte resiliente fuera de línea**:
- **Conectividad activa**: Registra experimentos, parámetros, métricas y artefactos serializados (`.joblib`, `.json`) en el servidor remoto de MLflow.
- **Fallback local**: Si el servidor MLflow no está disponible o `MLFLOW_TRACKING_URI` no está configurado, el tracker opera en memoria local sin interrumpir el pipeline ni arrojar excepciones no controladas.

---

## 7. Endpoint de Reentrenamiento (`POST /api/v1/ai/models/retrain`)

Permite ejecutar el pipeline de reentrenamiento bajo demanda con parámetros reproducibles:

```json
POST /api/v1/ai/models/retrain
{
  "dataset_version_id": "b3e94471-fec8-49ba-87b6-11fdf1641324",
  "candidate_architectures": ["tfidf_logreg", "tfidf_sgd"],
  "random_state": 42,
  "auto_promote_to_staging": true
}
```

Respuesta estructurada (`RetrainResponse`):
```json
{
  "run_id": "run-20260920-tfidf_logreg-42",
  "winner_architecture": "tfidf_logreg",
  "test_metrics": {
    "accuracy": 0.88,
    "f1_macro": 0.86,
    "precision_macro": 0.87,
    "recall_macro": 0.85
  },
  "promoted_to": "staging",
  "regression_passed": true,
  "violations": []
}
```
