# Market Relevance (6.16)

Agrega un concepto explícito de "relevancia de mercado" —
`knowledge.classifications.relevance_score`/`relevance_tier`,
`app/nlp/market_relevance.py`, usado desde `EmbeddingsStageExecutor`
(`app/nlp/semantic.py`) — distinto de `confidence_score` (6.7/6.15),
que mide cuánta confianza hay en la categoría ganadora, no si la
licitación es una oportunidad de mercado que vale la pena mirar.

## El concepto: temática vs comercial

- **Relevancia temática**: ¿es del rubro (accesibilidad/ayudas
  técnicas/discapacidad/adultos mayores)? Viene de las 3 señales que ya
  existen — `rule_score` (6.7, diccionario), `similarity_score` (6.8,
  embeddings), `model_score` (6.14, clasificador supervisado).
- **Relevancia comercial**: ¿sigue siendo una oportunidad activa? En v1
  se reduce a una sola señal — ver hallazgo de datos abajo.

`relevance_score = thematic_score * commercial_score` — multiplicativo,
no aditivo: una licitación puede ser 100% del rubro pero ya cerrada (no
se anula, pero se descuenta), o estar abierta pero no tener nada que ver
con el rubro (thematic_score=0 → relevance_score=0 sin importar
comercial).

## Hallazgo real: por qué la relevancia comercial es solo `fecha_cierre`

Antes de implementar, se inspeccionaron los ~11.8k registros reales de
`core.licitacion`: `monto_estimado`, `tipo`, `es_desierta` y
`es_adjudicada` están **100% NULL/False**. El endpoint de listado de
ChileCompra que alimenta el ETL (`LicitacionAPIItem`,
`app/integrations/chilecompra/models.py:9-19`) nunca trae esos campos, y
`raw_payload` tampoco se persiste — no hay ni un JSON crudo del que
extraerlos después. `estado` sí está poblado, pero como código numérico
crudo (`5,6,7,8,15,16` vistos en datos reales) sin una tabla de
decodificación confiable en el código; una búsqueda web para verificar
el mapeo oficial de ChileCompra dio resultados contradictorios, así que
no se hardcodeó una interpretación no verificada que podría invertir el
scoring silenciosamente.

**Decisión confirmada con el usuario**: la relevancia comercial de v1
usa solo `fecha_cierre` — la única señal real, poblada y verificable sin
ambigüedad hoy. `estado` decodificado y monto/tipo quedan
explícitamente fuera de alcance, documentados como gap de ETL (no
simulados) — ver "Fuera de alcance" abajo.

## La fórmula (`app/nlp/market_relevance.py`)

```python
normalized_rule_score = min(rule_score / _RULE_SCORE_SATURATION, 1.0)  # misma saturación que 6.7 (3.0)
thematic_score = max(normalized_rule_score, similarity_score, model_score)
commercial_score = 1.0 if still_open else 0.5   # fecha_cierre NULL o >= ahora => still_open
relevance_score = thematic_score * commercial_score
```

`thematic_score` usa el máximo de las 3 señales **crudas**, no solo la
que ganó la categoría en `combine_signals` (6.15) — para relevancia
importa que *alguna* señal haya detectado el rubro, aunque no haya sido
la que finalmente definió la categoría (p. ej. `similarity_score=0.6`
por debajo del umbral de 6.8 para fijar categoría, pero sigue siendo
evidencia real de relevancia temática).

`commercial_score = 0.5` para licitaciones cerradas, no `0.0` — esta es
una plataforma de inteligencia de mercado, no solo un asistente de
postulación (ver memoria de propósito del proyecto): una licitación
cerrada sigue teniendo valor histórico/de tendencia, no se descarta.

### `relevance_tier` (clasificación de relevancia)

| `relevance_score` | tier |
| --- | --- |
| `>= 0.66` | `high` |
| `>= 0.33` | `medium` |
| `> 0.0` | `low` |
| `== 0.0` | `not_relevant` |

Heurística inicial documentada, mismo criterio que
`_RULE_SCORE_SATURATION`/`_SIMILARITY_THRESHOLD` de fases anteriores —
tuning real es 6.23 (MLOps & Evaluation).

## Dónde corre y qué persiste

Se calcula en `EmbeddingsStageExecutor._update_or_create_classification`
(mismo lugar que combina las 3 señales para la categoría, 6.15) — no hay
un stage nuevo. `ClassificationStageExecutor` (6.7) no cambia:
`relevance_score`/`relevance_tier` quedan `NULL` hasta que corre la
etapa de embeddings, mismo patrón de nullability que ya tenían
`similarity_score`/`model_score`.

`explanation.relevance` (jsonb, mergeado junto a `matched_rules` de 6.7
y `hybrid` de 6.15, sin pisarse entre sí) guarda
`{algorithm_version, thematic_score, commercial_score, still_open}` —
`algorithm_version="relevance-v1"` satisface "Registrar versión del
algoritmo" sin agregar una columna nueva (mismo criterio que
`winning_method` en `explanation.hybrid`).

Migración: `20260828_0013_add_relevance_to_classifications.py`.

## Validación real contra el Gold Dataset `2026.2`

Se corrió el pipeline completo (reglas -> embeddings, con el
clasificador real de 6.14 cargado desde MinIO) sobre las 150 licitaciones
reales de `2026.2` (5 positivos reales, 145 negativos, etiquetado
asistido por IA — ver `docs/07-ai/gold-dataset.md`):

```
positivos (n=5):
  relevance_score=0.415 tier=medium
  relevance_score=0.410 tier=medium
  relevance_score=0.825 tier=high
  relevance_score=0.692 tier=high
  relevance_score=0.453 tier=medium

negativos (n=145) distribución de tier:
  medium=95  high=49  low=1

promedio relevance_score: positivos=0.559  negativos=0.529
```

**Disclaimer honesto**: la diferencia entre positivos y negativos es
mínima — `relevance_score` hoy no discrimina bien. Esto no es una falla
del cálculo en sí, es la propagación directa de dos limitaciones ya
documentadas: `similarity_score` tiende a dar valores moderados/altos
frente a casi cualquier texto de licitación pública (la taxonomía tiene
pocos conceptos, ~15 nodos, poco discriminativos entre sí — ver
`docs/07-ai/semantic-classification.md`), y el clasificador supervisado
de 6.14 tiene `f1_macro=0.326` en validación por el tamaño/desbalance
del dataset (ver `docs/07-ai/supervised-classification.md`). El cálculo
de `relevance_score` es correcto y reproducible; su poder discriminativo
real depende de que esas dos señales mejoren, que es exactamente lo que
6.23 (MLOps & Evaluation) y un Gold Dataset más grande van a atacar.

## Fuera de alcance (explícito)

- Señales comerciales de `monto_estimado`/`tipo`/`es_desierta`/
  `es_adjudicada`/`estado` decodificado — no hay datos reales
  confiables hoy (ver hallazgo arriba). Si el ETL se extiende para
  poblarlos, es una extensión natural de `compute_relevance` después,
  no un cambio de diseño.
- Pesos configurables / ponderación aprendida en vez de la heurística
  fija de v1 — 6.23.
- Exponer `relevance_score` vía API — eso es 6.18/6.19 (Service/
  Repository Layer).

## Ver también

- [`rule-classification.md`](rule-classification.md), [`semantic-classification.md`](semantic-classification.md), [`supervised-classification.md`](supervised-classification.md) — las 3 señales que alimentan `thematic_score`.
- [`hybrid-classification-pipeline.md`](hybrid-classification-pipeline.md) — `combine_signals`, la política de categoría (distinta de relevancia).
