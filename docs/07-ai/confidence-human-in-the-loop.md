# Confidence & Human-in-the-Loop (6.17)

Implementa el ciclo de revisión humana activa (**Human-in-the-Loop**, HITL) para predicciones de clasificación inciertas o contradictorias y la reincorporación de estas correcciones al **Gold Dataset** (`knowledge.gold_labels`), cerrando el ciclo de aprendizaje continuo del pipeline NLP.

---

## 1. Concepto y Estrategia de Confidence

### Confianza vs. Relevancia
En fases anteriores se establecieron tres métricas fundamentales:
- **`confidence_score`** (6.7, 6.8, 6.15): Mide la certidumbre en la categoría/subcategoría asignada por la señal ganadora (`combine_signals`).
- **`relevance_score`** (6.16): Mide si la licitación representa una oportunidad comercial en el nicho de accesibilidad/adultos mayores/ayudas técnicas, independiente de cuán certera sea la categoría.
- **`human_reviews`** (6.17): Provee la validación de ground truth humano. Cuando un revisor valida o corrige una predicción, el resultado se fija con `confidence_score = 1.0` y auditoría completa.

### Cuándo una predicción requiere revisión humana
Un score de confianza aislado no siempre cuenta toda la historia. Una licitación puede tener un `confidence_score = 0.72` aparentemente aceptable, pero provenir de un conflicto donde las reglas dijeron `health` y el clasificador supervisado dijo `construction` con margen estrecho.

El módulo `app/nlp/confidence.py` evalúa cuatro factores de riesgo:
1. **`low_confidence`**: El score ganador es inferior al umbral mínimo (`confidence_score < 0.65`).
2. **`conflicting_signals`**: Dos o más métodos (`rule`, `model`, `semantic`) propusieron categorías distintas con una diferencia de score menor o igual al margen (`margin <= 0.15`).
3. **`unassigned_category`**: La licitación presenta señales de relevancia comercial/temática (`relevance_tier` en `high` o `medium`), pero el clasificador no logró asignarle ninguna categoría.
4. **`borderline_relevance`**: La licitación es relevante para el negocio pero su confianza no alcanza el nivel alto (`0.65 <= confidence_score < 0.80`).

---

## 2. Umbrales Iniciales

Siguiendo el criterio de diseño de las fases 6.7 a 6.16, se definen heurísticas transparentes y reproducibles (documentadas y testeables, sujetas a calibración en 6.23):

| Parámetro | Valor Default | Propósito |
| --- | --- | --- |
| `DEFAULT_LOW_CONFIDENCE_THRESHOLD` | `0.65` | Clasificaciones con score bajo este valor son marcadas como `LOW` y enviadas a revisión |
| `DEFAULT_HIGH_CONFIDENCE_THRESHOLD` | `0.80` | Clasificaciones sin conflictos con score `>= 0.80` son consideradas `HIGH` y automatizables |
| `DEFAULT_CONFLICT_MARGIN` | `0.15` | Margen de score entre señales con categorías divergentes para activar alerta de conflicto |

---

## 3. Cola de Revisión Priorizada (`fetch_review_queue`)

No todas las predicciones de baja confianza ameritan el tiempo de un analista humano por igual: una licitación sobre áridos o asfaltos con baja confianza en salud no es prioritaria, mientras que una licitación de sillas de ruedas para adultos mayores con señales contradictorias es crítica para el negocio.

`compute_review_priority` (`app/nlp/human_review.py`) ordena la cola mediante:
$$\text{priority} = (\text{relevance\_signal} \times 0.6) + ((1.0 - \text{confidence\_score}) \times 0.4) + \text{boosts}$$

Donde:
- `relevance_signal`: `high` = 1.0, `medium` = 0.6, `low` = 0.2, `not_relevant` = 0.0.
- `boosts`: `+0.25` por señales contradictorias, `+0.20` por categoría sin asignar en licitaciones relevantes.
- La cola prioriza primero las licitaciones de alto impacto de negocio con mayor incertidumbre.

---

## 4. Acciones de Revisión Humana

El revisor dispone de dos caminos en `app/nlp/human_review_db.py`:

### A) Aceptar Clasificación (`accepted = True`)
- Confirma que la predicción del clasificador es correcta.
- Fija `confidence_score = 1.0` en `knowledge.classifications`.
- Inserta/actualiza en `knowledge.human_reviews` con `accepted = True`, manteniendo las categorías y relevancia actuales.
- Agrega metadata en `explanation.human_review` con `reviewed_by`, timestamp y notas.

### B) Modificar Clasificación (`accepted = False`)
- Permite cambiar categoría, subcategoría y relevancia (`relevant = True/False` y `relevance_tier`).
- **Exige un motivo (`reason`)**: Para mantener trazabilidad y explicar por qué el sistema falló.
- **Validaciones de consistencia** (`validate_review_decision`):
  - Si `relevant = False`: `category_code` y `subcategory_code` deben ser `None`, y `relevance_tier = 'not_relevant'`.
  - Si `relevant = True`: se exige categoría válida en la taxonomía vigente (`taxonomy-2026.2`). Si se indica subcategoría, se valida que pertenezca a dicha categoría.
- Actualiza `knowledge.classifications` con las nuevas categorías, ajusta relevancia, fija `confidence_score = 1.0` y registra la corrección en `explanation.human_review`.

---

## 5. Persistencia y Migración de Base de Datos

La tabla `knowledge.human_reviews` se actualizó mediante la migración Alembic `20260828_0014_add_relevance_to_human_reviews.py`:

```sql
ALTER TABLE knowledge.human_reviews ADD COLUMN relevant BOOLEAN;
ALTER TABLE knowledge.human_reviews ADD COLUMN relevance_tier VARCHAR(16);
```

### Estructura final de `knowledge.human_reviews`:
| Campo | Tipo | Significado |
| --- | --- | --- |
| `id` | UUID (PK) | Identificador de la revisión |
| `classification_id` | UUID (FK) | Clasificación revisada (`knowledge.classifications.id`, cascade) |
| `reviewer_id` | UUID (FK) | Usuario revisor (`users.id`, restrict) |
| `category_id` | Integer (FK) | Categoría final aprobada/corregida |
| `subcategory_id` | Integer (FK) | Subcategoría final aprobada/corregida |
| `accepted` | Boolean | `true` si se aceptó predicción, `false` si se corrigió |
| `relevant` | Boolean | Indica si la licitación pertenece al dominio de interés |
| `relevance_tier` | String(16) | Nivel de oportunidad (`high`, `medium`, `low`, `not_relevant`) |
| `reason` | Text | Justificación o motivo de la corrección |
| `created_at` / `updated_at` | Timestamptz | Trazabilidad temporal |

---

## 6. Sincronización con el Gold Dataset (`sync-gold`)

Las correcciones humanas no son solo registros pasivos de auditoría: son el combustible para el reentrenamiento supervisado del modelo (Fase 6.14 / 6.23).

`incorporate_feedback_to_gold_dataset` (`app/nlp/human_review_db.py`):
1. Recupera las revisiones humanas completadas.
2. Identifica la licitación y la versión activa del Gold Dataset (`knowledge.dataset_versions`).
3. Si la licitación ya existía en `knowledge.gold_labels`: actualiza `relevant`, `category_id`, `subcategory_id`, `labeled_by = "human-review:<email>"`, timestamp y notas.
4. Si es una licitación nueva: inserta la fila en `knowledge.gold_labels`.
5. Ejecuta `ensure_documents(connection, [licitacion_id])` para garantizar que `knowledge.documents` tenga el texto normalizado listo para el entrenamiento del clasificador (`build_tfidf_logreg_pipeline`).
6. Actualiza el conteo `record_count` y el `manifest.human_review_feedback` en `knowledge.dataset_versions`.

---

## 7. Operación vía CLI (`app/nlp/human_review_cli.py`)

Se provee una herramienta de línea de comandos completa para operar el ciclo HITL:

```bash
cd apps/backend

# 1. Inspeccionar la cola de revisión priorizada
python -m app.nlp.human_review_cli queue --threshold 0.65 --limit 20

# 2. Iniciar sesión interactiva de revisión humana en terminal
python -m app.nlp.human_review_cli review --reviewer-email tu@mercadoinsight.cl

# 3. Sincronizar las correcciones hacia el Gold Dataset activo
python -m app.nlp.human_review_cli sync-gold --version 2026.2

# 4. Ver reporte de métricas y estadísticas de revisión
python -m app.nlp.human_review_cli report
```

---

## 8. Fuera de Alcance (Explícito)

- **Acuerdo entre múltiples anotadores (Inter-annotator agreement)**: Por diseño de v1, cada licitación tiene un único revisor resolutivo. Casos de arbitraje entre múltiples anotadores corresponden a una fase posterior.
- **Calibración adaptativa de umbrales**: Los umbrales (0.65, 0.80, 0.15) son heurísticas iniciales fijas; su optimización basada en curvas ROC y precision/recall trade-off se abordará en la Fase 6.23 (MLOps & Evaluation).
- **Endpoints REST `/ai/reviews`**: La exposición HTTP de la cola y las revisiones pertenece a la Fase 6.21 (NLP API) y su capa de servicios/repositorios a 6.18 y 6.19.

---

## Ver también
- [`hybrid-classification-pipeline.md`](hybrid-classification-pipeline.md) — Combinación de señales y cálculo de `confidence_score` base.
- [`market-relevance.md`](market-relevance.md) — Cálculo de `relevance_score` y `relevance_tier`.
- [`gold-dataset.md`](gold-dataset.md) — Estructura y ciclo de vida de `knowledge.gold_labels`.
- [`supervised-classification.md`](supervised-classification.md) — Clasificador supervisado que se beneficia del feedback humano.
