# Product & Attribute Extraction (6.12)

Extiende el stage `KNOWLEDGE` existente (`KnowledgeStageExecutor`,
`app/nlp/knowledge_stage.py`) — no agrega un 4º `PipelineStage`. El
pipeline sigue en 3 stages (`classification -> embeddings -> knowledge`,
ver [`ner.md`](ner.md)). El motivo: el stage KNOWLEDGE ya cargaba
`core.licitacion_item` por licitación desde 6.11 (para la entidad
genérica `producto`); 6.12 reutiliza esa misma carga para identificar
**qué tipo** de producto es cada ítem y extraer sus atributos.

## `product_concept`: ya existía, implícito, en el diccionario

`app/nlp/dictionary.py` tiene 34 entries. La mayoría son temas
transversales sin `category_code` (geriatría, discapacidad,
rehabilitación — poblaciones/tópicos, no productos). Pero **16 entries ya
tienen `category_code`/`subcategory_code`** porque describen bienes/obras
tangibles:

| Concepto | Categoría/Subcategoría |
| --- | --- |
| silla_de_ruedas, andador, baston, muletas, ayuda_tecnica, audifono, protesis, ortesis, grua_de_traslado | health / medical-equipment |
| rampa_de_acceso, ascensor_accesible, bano_accesible, barra_de_apoyo, ampliacion_vanos_puertas, eliminacion_barreras_arquitectonicas | construction / civil-works |
| piso_antideslizante | construction / construction-materials |

**`product_concept` = un `DictionaryEntry` con `category_code is not
None`** (`app/nlp/product_concepts.py::product_concept_entries`). No se
creó un catálogo paralelo ni se tocó `dictionary.py`/`DictionaryEntry` —
es una función de filtrado pura sobre datos ya existentes.

## Por qué no se reutilizó `RuleEngine`

`RuleEngine`/`build_ruleset` (`app/nlp/rules.py`, 6.7) fue diseñado para
clasificar un documento completo: agrega todos los matches a un solo
category/subcategory ganador, y `RuleMatch.concept_code` es el *theme*
transversal del entry (`entry.theme.value`), no su concepto específico de
producto (`entry.concept`). Acá se necesita lo contrario: identificar,
independientemente, cada producto que menciona un ítem (0, 1 o varios).
`app/nlp/product_concepts.py::match_product_concepts` es un matcher
propio y más simple: substring casefold de cada `term`/`synonym` de cada
product_concept contra el texto del ítem — ninguno de los 16 entries de
producto tiene `abbreviations`, así que no hace falta la lógica regex
`\b...\b` de `build_ruleset`.

## Atributos extraídos (`app/nlp/product_attributes.py`)

Mismo criterio que marca/modelo en 6.11: alta precisión, baja cobertura
a propósito, vocabularios controlados y documentados en vez de
heurísticas de POS/capitalización (sin gold dataset — 6.13 — para
validarlas, son ruidosas en texto real).

| Atributo | Método | Ejemplo |
| --- | --- | --- |
| materiales | keyword list (acero, acero inoxidable, aluminio, madera, plástico, pvc, vidrio, goma, caucho, cuero, tela, nylon, fibra de carbono) | "acero inoxidable" |
| dimensiones | regex `NxNxN unidad` o `N unidad de ancho\|alto\|largo\|profundidad` (cm/mm/m) | "60 cm x 40 cm x 90 cm" |
| capacidad | regex `capacidad (de carga\|peso)? de? N (kg\|litros\|l)` / `hasta N (kg\|litros\|l)` | "120 kg" |
| características técnicas | keyword list (plegable, regulable en altura, reclinable, eléctrico, manual, con freno, antideslizante, impermeable) | "plegable" |
| cantidad / unidad | **no se extraen del texto** — se copian de `core.licitacion_item.cantidad`/`unidad`, ya poblados desde 6.2 (payload real de la API, `CoreLicitacionItemLoader`) | 5 / "unidades" |

Los vocabularios usan `\b...\b` (word boundary) para evitar la misma
clase de bug encontrada en 6.11 ("manual" no debe matchear dentro de
"manualidades", "acero" no debe matchear dentro de "aceros"). Incluyen
variantes con y sin tilde ("plástico"/"plastico", "eléctrico"/"electrico")
porque el texto de origen (`nombre`/`descripcion` crudos del ítem, no
`normalized_text`) conserva tildes.

## Persistencia

Dos tablas nuevas en `knowledge` (migración `20260828_0011`):

- **`knowledge.product_concepts`**: get-or-create por
  `(code, dictionary_version)` (`app/nlp/product_taxonomy_db.py`, mismo
  patrón que `resolve_category`/`resolve_subcategory` de
  `app/nlp/taxonomy_db.py`). Guarda `category_id`/`subcategory_id` — así
  "asociar productos con categorías" es automático: la asociación viene
  directo del `category_code`/`subcategory_code` que el dictionary entry
  ya trae.
- **`knowledge.products`**: una fila por `(licitacion_item_id,
  product_concept_id)` — un ítem puede mencionar más de un producto.
  `UNIQUE (licitacion_item_id, product_concept_id)` +
  `ON CONFLICT DO NOTHING` en el insert: reprocesar el mismo documento no
  duplica filas. `classification_id` nullable, igual criterio que
  `knowledge.entities` en 6.11 (última clasificación de la licitación).
  `confidence_score = 1.0` siempre que hay match — es un substring exacto
  de un término conocido, no hay score parcial que calibrar sin datos
  (6.23 es donde correspondería tunear esto).

Un ítem sin producto conocido (ej. "Servicio de aseo general") no genera
fila en `knowledge.products` — no es una falla, ya quedó como entidad
`producto` genérica por 6.11.

## Por qué no se resucitó `core.producto`/`core.categoria`

`core.licitacion_item.producto_id`/`categoria_id` apuntan a un catálogo
legacy (`core.producto`/`core.categoria`) nunca poblado — no hay fuente
UNSPSC. Poblarlo habría creado una segunda taxonomía de categorías
desconectada de `knowledge.categories`/`subcategories` (la que 6.5-6.9 ya
construyeron y que `knowledge.classifications` usa), y de todos modos no
tiene dónde guardar materiales/dimensiones/capacidad/características —
se habrían necesitado tablas nuevas igual. `knowledge.product_concepts`/
`knowledge.products` mantienen todo el conocimiento semántico derivado en
un solo lugar consistente.

## Validado con datos reales

Contra Postgres dev real: licitación con 3 ítems — "Silla de ruedas"
(marca Invacare, acero inoxidable, 60x40x90 cm, 120 kg, con freno,
plegable), "Rampa de acceso" (aluminio, 80 cm de ancho, antideslizante) y
"Servicio de aseo general" (sin producto conocido). Resultado: 2 filas en
`knowledge.products` (el ítem de aseo, correctamente, sin fila), cada una
con `category_id`/`subcategory_id` resueltos, `cantidad`/`unidad`
copiados del ítem, atributos extraídos correctamente, y
`classification_id` enlazado. Reprocesar el mismo documento no duplicó
filas (`ON CONFLICT DO NOTHING` verificado). Limpieza al final, sin datos
de prueba dejados.

## Fuera de alcance (explícito)

- Ampliar el diccionario con más `product_concept` fuera del dominio
  salud/accesibilidad ya cubierto por 6.7 — no se agranda en esta fase.
- Vocabularios de materiales/características técnicas exhaustivos — lista
  inicial documentada y extensible, no pretende cobertura total.
- Descomponer `dimensiones` en ancho/alto/profundidad estructurados —
  texto normalizado es suficiente por ahora.

## Ver también

- [`ner.md`](ner.md) — `KnowledgeStageExecutor`, el stage que 6.12 extiende.
- [`rule-classification.md`](rule-classification.md) — `RuleEngine`/`build_ruleset`, por qué no se reutilizan acá.
- [`architecture.md`](architecture.md) — orden del pipeline (sigue en 3 stages).
