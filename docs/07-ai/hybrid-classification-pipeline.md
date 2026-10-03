# Hybrid Classification Pipeline (6.15)

Reemplaza la política implícita de combinación entre reglas (6.7) y
semántica (6.8) por una explícita, documentada, y que ahora también
considera el modelo supervisado (6.14) — `app/nlp/hybrid_classification.py`,
usado desde `EmbeddingsStageExecutor` (`app/nlp/semantic.py`), el stage
que ya tenía visibilidad de las 3 señales en el momento correcto.

## La política anterior (implícita, pre-6.15)

`EmbeddingsStageExecutor._update_or_create_classification` solo pisaba
la categoría de las reglas si estas **no habían encontrado nada**
(`existing is None`). Si las reglas matchearon algo, ganaban siempre, sin
importar cuán débil fuera su `rule_score` frente a un `similarity_score`
mucho más alto. No había lugar para una tercera señal (el modelo no
existía todavía).

## La política v1 (6.15): gana el score más alto

`combine_signals` (`app/nlp/hybrid_classification.py`) recibe las 3
señales (`SignalResult(method, category_code, subcategory_code, score)`)
y devuelve la de mayor `score` **entre las que sí produjeron una
categoría** — una señal sin match (regla que no disparó, similitud bajo
umbral, modelo prediciendo `not_relevant`) no compite, solo aporta su
score crudo a `explanation`. Empate (raro con floats, pero determinístico
por diseño): gana regla > modelo > semántica — regla es la señal más
determinística/auditable, el modelo ya fue seleccionado y evaluado
(6.14), semántica es la más propensa a falsos positivos con una
taxonomía todavía poco poblada.

Heurística inicial, documentada — igual criterio que
`_RULE_SCORE_SATURATION`/`_SIMILARITY_THRESHOLD` de fases anteriores; el
tuning real (ponderar en vez de "winner-takes-all", por ejemplo) es 6.23.

## Dónde corre (no hay un 4º stage)

`EmbeddingsStageExecutor` ya era el stage que veía la fila de
`knowledge.classifications` que dejó `ClassificationStageExecutor`
(6.7) y calculaba su propio `similarity_score` — 6.15 lo extiende para
además correr el clasificador persistido (6.14, `predict`/`predict_proba`
sobre el mismo `normalized_text` que ya tenía cargado) y hacer la
combinación final ahí mismo. El pipeline sigue en 3 stages
(`classification -> embeddings -> knowledge`, cerrado desde 6.11/6.12).

`classifier` es `None` por defecto — sin un modelo entrenado todavía
(o durante tests), el pipeline sigue funcionando solo con reglas+semántica,
igual que antes de 6.14. El worker real (`app/worker/nlp_tasks.py`) lo
carga una vez al arrancar (`_load_classifier()`): busca el
`knowledge.model_versions` de `kind='classifier'` más reciente en
`production` (o `staging` si no hay ninguno en producción), descarga el
artefacto de MinIO, `joblib.load`. Mismo patrón que la carga del modelo
de embeddings (pagar el costo una vez al inicio del proceso, no por job).

## Cómo queda `knowledge.classifications`

| Campo | Quién lo escribe | Significado |
| --- | --- | --- |
| `rule_score` | `ClassificationStageExecutor` (6.7) | Score acumulado de reglas que dispararon |
| `similarity_score` | `EmbeddingsStageExecutor` (6.8) | Similitud coseno con el concepto de taxonomía más cercano |
| `model_score` | `EmbeddingsStageExecutor` (6.15) | Probabilidad de la clase predicha por el clasificador |
| `confidence_score` | `EmbeddingsStageExecutor` (6.15) | El score de la señal ganadora (`combine_signals`) |
| `category_id`/`subcategory_id` | `EmbeddingsStageExecutor` (6.15) | De la señal ganadora |
| `model_version_id` | `EmbeddingsStageExecutor` (6.15) | El `ModelVersion` del clasificador cargado (no el del modelo de embeddings — ver nota abajo) |
| `dataset_version_id` | `EmbeddingsStageExecutor` (6.15) | El Gold Dataset con el que se entrenó/seleccionó ese clasificador |
| `explanation` | Ambos stages, mergeado | `matched_rules` (6.7) + `hybrid: {scores, categories, winning_method}` (6.15) — no se pisan entre sí |

**Nota sobre `model_version_id`**: el schema tiene una sola columna FK a
`knowledge.model_versions` en `Classification`. El modelo de *embeddings*
(kind=`embedding`) se registra igual que antes en
`knowledge.embeddings.model_version_id` — es un dato distinto (qué modelo
generó el vector) del clasificador *supervisado* (kind=`classifier`) que
ahora ocupa `classifications.model_version_id` — ese es el "modelo" al
que se refiere el checklist de 6.15 ("Registrar versión de modelo").

## Validado con datos reales

Licitación real de prueba ("Suministro de sillas de ruedas y andadores
para adultos mayores en situación de discapacidad") contra Postgres dev +
MinIO reales, con el clasificador entrenado en 6.14 cargado de verdad:

```
rule_score=1.0 similarity_score=0.719 model_score=0.760
confidence_score=1.0 category=health/medical-equipment
winning_method=rule
```

Las 3 señales dispararon con scores distintos, la regla ganó (score más
alto), `explanation` conserva `matched_rules` de 6.7 y agrega el desglose
`hybrid`, `model_version_id`/`dataset_version_id` quedaron enlazados al
clasificador real de 6.14. Limpieza al final, sin datos de prueba
dejados.

## Fuera de alcance (explícito)

- Ponderar señales en vez de "el más alto gana" — 6.23.
- Que el modelo prediga subcategoría (hoy solo predice categoría o
  `not_relevant`, sin datos reales suficientes por subcategoría) — cuando
  el Gold Dataset tenga más señal, es una extensión natural de 6.14.
- Selección automática de `production` — sigue siendo manual (ver 6.14).

## Ver también

- [`rule-classification.md`](rule-classification.md) — `ClassificationStageExecutor`, la señal `rule`.
- [`semantic-classification.md`](semantic-classification.md) — la señal `semantic` y `EmbeddingsStageExecutor` original.
- [`supervised-classification.md`](supervised-classification.md) — de dónde sale el clasificador y por qué sus métricas todavía son solo de validación del pipeline.
