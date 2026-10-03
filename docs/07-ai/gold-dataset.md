# Gold Dataset (6.13)

Dataset etiquetado por humanos que 6.14+ (clasificación supervisada)
necesita para entrenar/evaluar — sin eso, "medir accuracy/F1/matriz de
confusión" no tiene contra qué comparar.

## Qué significa "relevante" en este dominio

El producto (taxonomía/diccionario de 6.5-6.9) apunta específicamente a
accesibilidad/ayudas técnicas/adultos mayores — una porción minúscula de
todas las licitaciones de Mercado Público. `relevant` responde: **¿esta
licitación pertenece al nicho que el producto analiza?** No es lo mismo
que "tiene una categoría de la taxonomía" — la taxonomía tiene una
categoría catch-all (`general-supplies`) para que cualquier licitación
tenga dónde caer si hiciera falta, pero eso no la hace relevante para
este análisis de mercado.

## Estructura (`knowledge.gold_labels`)

| Campo | Sentido |
| --- | --- |
| `dataset_version_id` | FK a `knowledge.dataset_versions` — agrupa una "corrida" de muestreo/etiquetado |
| `licitacion_id` | FK a `core.licitacion` |
| `relevant` | `NULL` = pendiente de etiquetar; `true`/`false` una vez etiquetada |
| `category_id` / `subcategory_id` | Solo se setean cuando `relevant = true` |
| `taxonomy_version` | Versión de la taxonomía usada al etiquetar (trazabilidad si la taxonomía cambia después) |
| `labeled_by` | Identificador del etiquetador (email) |
| `labeled_at` | Timestamp del etiquetado |
| `split` | `train`/`validation`/`test`, asignado después de etiquetar |
| `notes` | Texto libre opcional |

Una fila por `(dataset_version_id, licitacion_id)` — reetiquetar es un
`UPDATE`, no crea una fila nueva (permite corregir sin duplicar).

## Por qué el muestreo es estratificado, no aleatorio puro

Una muestra puramente aleatoria de licitaciones reales tendría ~0
ejemplos positivos en un N chico de etiquetar a mano — el nicho es
demasiado angosto frente al total de Mercado Público. Eso volvería
`relevant` un label trivial (siempre `false`) y el dataset resultante
inútil para entrenar/evaluar el clasificador de 6.14.

`select_sample` (`app/nlp/gold_dataset.py`) arma la muestra en dos
estratos: una porción (`--keyword-share`, default 50%) sale de
licitaciones cuyo `nombre`/`descripcion` ya matchea algún surface form
del diccionario semántico (candidatas positivas), el resto es aleatorio
uniforme sobre el resto del corpus ingerido (clase negativa real).
Determinístico vía `random.Random(seed)` — mismo seed, misma muestra.
Documentado explícitamente como representativo de **la tarea de
clasificación**, no de la distribución cruda de tráfico de Mercado
Público.

## Protocolo de etiquetado

1. `sample` trae y enriquece (`nombre`+`descripcion`+ítems reales, vía
   `enrich_licitacion_detail`, el mismo helper que usa el Celery task) la
   muestra, y crea las filas pendientes en `gold_labels`.
2. `label --labeled-by <tu email>` — recorre las filas pendientes,
   pregunta si es relevante y, si lo es, pide categoría/subcategoría de
   la taxonomía vigente (menú numerado) y notas opcionales. Se puede
   interrumpir en cualquier momento (`q`) — lo que falta queda pendiente
   para la próxima corrida. Reetiquetar una fila ya hecha es soportado
   (correr `label` de nuevo sobre las mismas filas vía una futura opción
   `--relabel`, o directo un `UPDATE` manual si hace falta corregir algo
   puntual).
3. `split` — asigna `train`/`validation`/`test` (70/15/15 por defecto)
   **estratificado por categoría** (`assign_splits`), para que una
   categoría rara no quede 100% en un solo split.
4. `report` — imprime distribución de clases, clases desbalanceadas
   (< 10% del total, ajustable), inconsistencias automáticas, y conteo
   por split. Correrlo después de etiquetar y de nuevo después de split.
5. `finalize` — exige que no queden filas pendientes y que todas tengan
   `split`; actualiza `knowledge.dataset_versions.record_count`/
   `manifest` con la distribución final. Esto es "crear la primera
   versión del Gold Dataset" — solo tiene sentido correrlo con etiquetas
   humanas reales.

Con un solo etiquetador (vos), "revisar inconsistencias" no es acuerdo
entre anotadores — son los chequeos automáticos de `report`
(`detect_inconsistencies`): `relevant=true` sin categoría,
`relevant=false` con categoría igual seteada, o una subcategoría que no
pertenece a la categoría de la misma fila. Corregir es re-etiquetar esa
fila.

## Cómo correr el CLI

```bash
cd apps/backend
python -m app.nlp.gold_dataset_cli sample --size 40 --keyword-share 0.5
python -m app.nlp.gold_dataset_cli label --labeled-by tu@email.com
python -m app.nlp.gold_dataset_cli split
python -m app.nlp.gold_dataset_cli report
python -m app.nlp.gold_dataset_cli finalize
```

`label` es el único subcomando pensado para correr interactivo en tu
propia terminal — es el paso que produce el ground truth real y no se
puede scriptear ni simular.

## Bug real encontrado validando con datos reales: la ingesta nunca commiteaba

El primer ticket probado no tenía acceso a los endpoints de listado
(`por_fecha`, `diarias()`, `por_estado`) — devolvían 0 sin error; solo
`por_codigo` (lookup exacto) funcionaba. Con un ticket nuevo del usuario,
los listados sí devolvieron datos reales (1159+ licitaciones vía
`diarias()`), pero la primera ingesta acotada (14 días, `force_backfill`)
reportó `inserted: 11798` y aun así `core.licitacion` quedó en 0 filas.

Causa: `CoreLicitacionLoader.load()` (`app/etl/loading/core_schema.py`) y
`enrich_licitacion_detail` (`app/etl/enrichment/licitacion_detail.py`)
abrían una `Connection`, ejecutaban los `INSERT`/`UPDATE`, y llamaban
`connection.close()` **sin `connection.commit()`** — con SQLAlchemy Core
(no-autocommit), cerrar sin commitear descarta todo implícitamente. Los
`LoadResult`/métricas se calculan en memoria antes del descarte, así que
todo parecía exitoso. `staging.raw_ingestion_events` y el checkpoint
(`etl.etl_incremental_checkpoints`) sí commiteaban correctamente (usan
`Session`/otro código), lo que confirmó que el problema era específico
de estos dos loaders y no de todo el pipeline — permitió reprocesar sin
volver a golpear la API real.

Los tests existentes de ambos (`test_core_schema.py`,
`test_licitacion_detail.py`) usaban fakes sin `commit()`/`rollback()` en
absoluto, así que la ausencia del commit real era invisible para la
suite pese a que `result.inserted` reportaba éxito. Corregido agregando
`connection.commit()` (y `rollback()` en el `except`) en ambos, con
tests de regresión (`test_load_commits_the_transaction`,
`test_enrich_commits_the_item_connection`) que ahora sí verifican que se
llame `commit()`, no solo que las métricas cuadren.

## Estado real al cierre de esta fase — corrida real completa

Con el ticket nuevo y el bug de arriba corregido: ingesta acotada real
(14 días, ~11.8k licitaciones reales en `core.licitacion`), muestra
estratificada real de 40 (`sample`), enriquecidas con `descripcion`/ítems
reales.

**El etiquetado de esta primera versión es asistido por IA, no humano**:
por decisión explícita del usuario en esta sesión, las 40 licitaciones
fueron etiquetadas leyendo el texto real de cada una, pero por Claude, no
por una persona — `labeled_by = "claude-ai-assisted"` en cada fila, y
`manifest.labeled_by_counts` en `knowledge.dataset_versions` lo deja
explícito para quien use este dataset después (6.14 debería tratarlo como
bootstrap, no como set de evaluación confiable, hasta que un humano lo
revise). Resultado: 2/40 relevantes (ambas `health/assistive-technology`
— "Suministro de ayudas técnicas" con bastones para vestir para personas
con discapacidad física, y equipamiento de terapia física para
rehabilitación), 38/40 no relevantes — la mayoría de las candidatas por
keyword resultaron ser falsos positivos al leer el texto completo (p.ej.
"REHABILITACION DE HITOS DE ACCESO" es sobre infraestructura vial rural,
no accesibilidad para discapacidad), lo cual es exactamente la clase de
precisión que el filtro por keyword no puede resolver solo — confirma
por qué hace falta juicio (humano o AI-asistido) sobre el texto real y
no alcanza con el match léxico.

`report` marcó correctamente la clase `health` como desbalanceada (5%,
bajo el umbral de 10%) y no encontró inconsistencias. `split`
(70/15/15 estratificado) y `finalize` corrieron sin problemas —
`knowledge.dataset_versions` tiene su primera fila real
(`gold-dataset`/`2026.1`, `record_count=40`, `manifest.status=ready`).

Ver `TODO.md` 6.13 para el detalle de qué quedó `[x]` y qué `[ ]`.

## Fuera de alcance (explícito)

- Acuerdo entre múltiples anotadores (inter-annotator agreement) — un
  solo etiquetador por ahora; si se suma un segundo, `detect_inconsistencies`
  tendría que extenderse para comparar entre etiquetadores, no solo
  chequear consistencia interna de una fila.
- Balancear activamente las clases (oversampling/undersampling) —
  `detect_imbalance` solo reporta, no corrige; corregir desbalance real
  es una decisión de 6.14 (pesos de clase, muestreo adicional dirigido).

## Ver también

- [`rule-classification.md`](rule-classification.md) — la taxonomía/diccionario que definen categoría/subcategoría y los términos usados para el muestreo por keyword.
- [`architecture.md`](architecture.md) — contexto general del pipeline NLP.
