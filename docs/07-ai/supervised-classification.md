# Supervised Classification (6.14)

Dos baselines entrenados y evaluados sobre el Gold Dataset (6.13), el
ganador persistido en MinIO y registrado como `knowledge.model_versions`
— `app/nlp/classifier_training.py` (lógica pura), `classifier_training_db.py`
(persistencia), `classifier_training_cli.py` (`python -m
app.nlp.classifier_training_cli train`).

## Los dos baselines

| | Features | Clasificador |
| --- | --- | --- |
| `tfidf_logreg` | `TfidfVectorizer` (unigramas+bigramas) sobre `normalized_text` | `LogisticRegression` |
| `embeddings_logreg` | Embeddings congelados (`sentence-transformers`, mismo modelo de 6.8/6.9) como "linear probe" | `LogisticRegression` |

Ambos con `class_weight="balanced"`: el Gold Dataset real está fuertemente
sesgado hacia `not_relevant` (~95-97%) — sin ese ajuste el modelo puede
alcanzar accuracy alta con solo predecir siempre la clase mayoritaria.
Heurística inicial documentada, mismo espíritu que
`_RULE_SCORE_SATURATION`/`_SIMILARITY_THRESHOLD` de fases anteriores —
tuning real es 6.23 (MLOps & Evaluation).

## Por qué se selecciona por `f1_macro`, no `accuracy`

Con ~95% de una sola clase, un modelo que predice siempre "not_relevant"
ya tiene ~95% de accuracy sin haber aprendido nada útil. `f1_macro`
promedia el F1 de cada clase por igual (no ponderado por soporte), así
que un modelo que ignora las clases minoritarias queda penalizado. La
selección del ganador (`train_and_select`) compara `f1_macro` en
`validation`, y el número final que se reporta es el de `test` (nunca
tocado hasta ese punto) — evaluar en el mismo split que se usó para
elegir habría inflado el resultado.

## Métricas reales obtenidas (dataset `2026.2`, 150 registros)

Ganador: `tfidf-logreg`. `train=106, validation=23, test=21`.

```
validation: accuracy=0.957 f1_macro=0.326
test:       accuracy=1.000 f1_macro=0.333
```

**Disclaimer honesto**: estos números no describen un clasificador
utilizable todavía. El Gold Dataset real tiene solo 5 ejemplos positivos
en total (2 `health/assistive-technology` de la versión `2026.1` — no
usados acá, dataset distinto — más 4 `health` y 1 `construction` en
`2026.2`) repartidos entre train/validation/test — el split de `test`
terminó con 0 ejemplos positivos (`construction` también quedó en 0 en
`validation`), así que `test accuracy=1.0` es trivial (predecir siempre
`not_relevant` da ese resultado) y las métricas por clase de las
categorías minoritarias no tienen soporte suficiente para ser
confiables. Esta corrida valida que el **pipeline** funciona de punta a
punta contra datos reales (Postgres + MinIO) — no que el modelo esté
listo para producción. Ver `docs/07-ai/gold-dataset.md` para el mismo
disclaimer aplicado al dataset.

## Persistencia

- El pipeline ganador (`sklearn.pipeline.Pipeline` completo — vectorizador/encoder + clasificador juntos) se serializa con `joblib` y se sube a MinIO (`ml-models/<model_name>/<version>.joblib`, bucket nuevo `MINIO_BUCKET_ML_MODELS`, reusa `MinioObjectStorage` de `app/infrastructure/storage/minio_storage.py`).
- `knowledge.model_versions`: `status="staging"` — nunca `"production"` automáticamente (`validate_model_transition` en `app/nlp/contracts.py` ya define esa transición para cuando corresponda promoverlo, es una decisión de negocio no del pipeline). `parameters.dataset_version_id` guarda qué Gold Dataset se usó para entrenar/seleccionar (no hay columna FK dedicada en el schema, ver 6.13). `metrics` guarda accuracy/precision/recall/F1/macro-F1/matriz de confusión de train, validation y test.
- Reentrenar con el mismo `name`+`version` actualiza la fila existente (`register_model_version` es get-or-create/update, `app/nlp/classifier_training_db.py`) — no duplica.

## Cómo correr

```bash
cd apps/backend
python -m app.nlp.classifier_training_cli train --dataset-version <uuid opcional> --version v1
```

Sin `--dataset-version`, usa el `dataset_versions` más reciente con
`name="gold-dataset"`.

## Fuera de alcance (explícito)

- Promoción a `production` — manual, fuera de este pipeline.
- Modelos más allá de los 2 baselines (SVM, gradient boosting, fine-tuning
  del embedding, etc.) — evaluar candidatos adicionales es una extensión
  natural una vez el Gold Dataset tenga más señal real.
- Reentrenamiento automático / triggers por nuevo dato — CLI manual por ahora.

## Ver también

- [`gold-dataset.md`](gold-dataset.md) — de dónde sale el dataset de entrenamiento, y por qué es chico/desbalanceado todavía.
- [`hybrid-classification-pipeline.md`](hybrid-classification-pipeline.md) — 6.15, cómo `model_score` se combina con `rule_score`/`similarity_score`.
