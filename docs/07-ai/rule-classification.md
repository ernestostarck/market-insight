# Rule-Based Classification

Primer nivel de clasificación (`PipelineStage.CLASSIFICATION`, el primer
`StageExecutor` real registrado en `STAGE_REGISTRY`,
`app/worker/nlp_tasks.py`). Determinístico: mismo texto + misma versión de
diccionario/taxonomía siempre produce el mismo resultado.

## Estructura de `Rule`

`app/nlp/rules.py`:

```python
@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    concept_code: str        # siempre un DomainConcept.code real (puente 6.5)
    category_code: str
    keyword: str              # literal, o patrón regex si is_regex
    weight: float = 1.0
    version: str = "1"
    subcategory_code: str | None = None
    active: bool = True
    is_regex: bool = False
```

`RuleEngine.evaluate(normalized_text)` recorre las reglas activas: si
`is_regex`, hace `re.search` (compilado una vez en `__init__`, no por
texto); si no, substring `casefold()`. Agrega el peso de cada match por
`(category_code, subcategory_code)` y devuelve el par con mayor score
(`RuleEvaluation`).

## El conjunto inicial: `build_ruleset`

`build_ruleset(dictionary, taxonomy)` genera una `Rule` por cada forma de
superficie de cada `DictionaryEntry` (`app/nlp/dictionary.py`):

- **`concept_code`** es siempre `entry.theme.value` — el puente formal con
  la taxonomía (`DomainConcept.code == DomainTheme.value`, ver
  [`taxonomy.md`](taxonomy.md)).
- **`category_code`/`subcategory_code`**: si la entrada del diccionario ya
  trae los suyos (caso producto-específico, ej. "silla de ruedas" ->
  `health/medical-equipment`), se usan tal cual. Si no (los 9 temas
  transversales que 6.4 dejó sin categoría propia), se derivan del hogar
  del concepto en la taxonomía vía `Taxonomy.locate(concept_code)`.

### Términos/sinónimos vs. abreviaciones — por qué regex "cuando corresponda"

La primera corrida contra licitaciones reales de ChileCompra (validación
de esta fase) encontró un falso positivo real: la abreviación `"to"`
(terapia ocupacional) hacía match por substring dentro de "**to**rio",
"servi**cio**"... espera, dentro de palabras como "audi**to**rio" y
"contra**to**" — cualquier palabra española que contenga las letras "to"
seguidas. Un término completo como "silla de ruedas" es seguro como
substring (frase de varias palabras, prácticamente nunca aparece dentro de
otra palabra), pero una abreviación de 2-5 caracteres no lo es.

Por eso `build_ruleset` distingue el origen de cada forma de superficie:
`entry.term`/`entry.synonyms` generan reglas de substring simple
(`is_regex=False`); `entry.abbreviations` generan reglas regex con límite
de palabra (`is_regex=True`, patrón `\b<abreviación>\b`). Test de
regresión: `tests/nlp/test_rule_engine.py::test_short_abbreviation_rule_does_not_match_inside_unrelated_words`.

## Persistencia — `ClassificationStageExecutor`

`app/nlp/classification.py`, mismo estilo Core (`Connection`+`text()`) que
`CoreLicitacionLoader` (`app/etl/loading/core_schema.py`) — es el patrón
establecido para escribir desde un Celery task síncrono.

1. Busca `knowledge.documents` por `(licitacion_id, content_hash)`. Sin
   documento preprocesado, el stage falla (`return False`) — no hay nada
   que clasificar.
2. Corre `RuleEngine.evaluate()` sobre `normalized_text`.
3. Si hubo match: get-or-create `knowledge.categories`/`subcategories`
   (por `code`+`taxonomy_version`) y `knowledge.rules` (por `code`+
   `version`, una fila por regla que hizo match) — la primera vez que
   corre el pipeline, estas tablas se van poblando solas; no hay un seed
   separado.
4. `confidence_score = min(rule_score / 3.0, 1.0)` — heurística inicial
   documentada (3+ de peso acumulado ≈ confianza plena). El ajuste real es
   de 6.23 (MLOps & Evaluation).
5. Inserta `knowledge.classifications` con `explanation` JSON
   (`matched_rules`: `rule_id`, `concept_code`, `keyword`, `weight` — la
   traza de "regla utilizada"). Sin match, igual se inserta una fila
   (`category_id`/`subcategory_id` `NULL`, `confidence_score=0.0`) — no
   encontrar nada es un resultado válido, no una falla del stage.

## Rule preview síncrono (`POST /classify`)

`app/db/dependencies.py::get_nlp_service()` ahora construye el
`RuleEngine` con el ruleset real (`build_ruleset(load_initial_dictionary(),
load_initial_taxonomy())`, una sola vez a nivel de módulo) — antes corría
con un motor vacío. Sigue siendo el preview advisory de ADR 0002: nunca
persiste, no pasa por `NLPJobRequest`.

## Validado contra licitaciones reales

Con la ChileCompra API real: 3 licitaciones activas reales, ninguna
relacionada al dominio — el resultado correcto es `category_id=NULL` en
las 3 (y así fue, después de corregir el bug de "to"). Con texto sintético
mezclando varios términos reales del diccionario ("discapacidad",
"ELEAM"): clasificó correctamente a `health/geriatric-care`, con
`explanation` trazando ambas reglas usadas. Ambas corridas contra el
Postgres dev real, con limpieza explícita después (sin dejar datos de
prueba).

## Ver también

- [`semantic-dictionary.md`](semantic-dictionary.md) — `DomainDictionary`/`DictionaryEntry`.
- [`taxonomy.md`](taxonomy.md) — el puente `DomainConcept.code == DomainTheme.value`.
- [`architecture.md`](architecture.md) — dónde vive `CLASSIFICATION` en el pipeline.
