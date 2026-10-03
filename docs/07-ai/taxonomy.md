# Taxonomía

La taxonomía vigente es **`taxonomy-2026.3`**, en `app/nlp/data/taxonomy-2026.3.json`,
cargada por `load_initial_taxonomy()`/`load_taxonomy(version)` (`app/nlp/taxonomy.py`).
Las versiones anteriores quedan congeladas sin tocar — invariante append-only
(ver abajo). `load_taxonomy("2026.1")`/`load_taxonomy("2026.2")` las siguen
cargando tal cual, para trazabilidad histórica.

## Jerarquía de 3 niveles

`Categoría → Subcategoría → Concepto`. Las primeras dos existían desde
`2026.1` (seis categorías genéricas: tecnología, salud, construcción,
transporte, servicios profesionales, suministros generales; cada una con dos
subcategorías). `2026.2` agrega el tercer nivel, `Concepto`
(`DomainConcept` — código, nombre, descripción, anidado dentro de una
`TaxonomySubcategory`), y tres subcategorías nuevas para darle hogar:

- `health/geriatric-care` ("Atención geriátrica y adulto mayor") — conceptos `geriatria`, `adultos_mayores`
- `health/assistive-technology` ("Ayudas técnicas y rehabilitación") — conceptos `discapacidad`, `movilidad_reducida`, `ayudas_tecnicas`, `rehabilitacion`
- `construction/accessibility-adaptation` ("Accesibilidad y adaptación de espacios") — conceptos `accesibilidad`, `prevencion_caidas`, `adaptacion_espacios`

El resto de las subcategorías (tecnología, salud/equipamiento-médico,
salud/insumos-médicos, construcción/obras-civiles,
construcción/materiales-construcción, transporte, servicios-profesionales,
suministros-generales) no tienen conceptos — `concepts: tuple[DomainConcept, ...] = ()`.

## Por qué estos 3 conceptos nuevos y no una 7ma categoría

Al construir 6.4 (Domain Dictionary) se encontró que sus 9 temas (geriatría,
adultos mayores, discapacidad, movilidad reducida, accesibilidad, ayudas
técnicas, prevención de caídas, rehabilitación, adaptación de espacios) son
**poblaciones/temas transversales**, no categorías de producto — no mapeaban
1:1 a las 6 categorías genéricas. Se descartó una 7ma categoría top-level:
`health` y `construction` ya eran el fit natural para los términos
específicos que 6.4 sí había podido categorizar (una silla de ruedas es
salud/equipamiento-médico; una rampa es construcción/obras-civiles), así que
las subcategorías nuevas reusan esas dos categorías en vez de crear una
tercera rama paralela.

## El puente formal con el diccionario semántico

Los códigos de `DomainConcept` son **exactamente** los mismos strings que
`DomainTheme.value` (`app/nlp/dictionary.py`) — `geriatria`,
`adultos_mayores`, etc. Esa identidad es el puente entre taxonomía y
diccionario: no hay una tabla de mapeo indirecta. Se verifica con un test de
integración (`tests/nlp/test_dictionary.py::test_domain_themes_match_taxonomy_concepts_exactly`)
que el set de valores de `DomainTheme` sea exactamente igual al set de
códigos de concepto de la taxonomía real — si alguno de los dos se desvía,
la suite falla. Ver también [`semantic-dictionary.md`](semantic-dictionary.md).

## Identificadores estables

Los códigos son identificadores estables. Categorías/subcategorías usan
minúsculas y kebab-case; los conceptos usan snake_case (reusan los valores de
`DomainTheme`) — por eso `_STABLE_CODE` (`app/nlp/taxonomy.py`) permite tanto
`-` como `_`. Los nombres y las descripciones pueden corregirse en una
versión posterior; un código ya publicado no se reutiliza con otro
significado.

## Incorporar una categoría, subcategoría o concepto

1. Copiar el catálogo a una nueva versión (ej. `taxonomy-2026.3`) — nunca se edita una versión ya publicada.
2. Añadir la categoría/subcategoría/concepto con código estable, nombre y descripción semántica.
3. Ejecutar las pruebas de `tests/nlp/test_taxonomy.py` (y `test_dictionary.py` si toca conceptos) y crear una migración que cargue la versión nueva, sin actualizar filas históricas.
4. Actualizar reglas, Gold Dataset y modelos para referenciar la nueva versión antes de promoverla.

Una clasificación siempre conserva la versión de taxonomía utilizada; las
categorías, subcategorías y conceptos se relacionan por anidamiento en el
propio `Taxonomy` (persistencia en `knowledge.categories`/`knowledge.subcategories`
vía `category_id`, y `knowledge.concepts` — entidad que crea 6.6 — quedan
fuera de alcance de esta fase; `taxonomy.py` no escribe a la base de datos
todavía).

## `taxonomy-2026.3`: categoría `apparel` (vestimenta moldeadora)

Agrega una **séptima categoría**, `apparel` ("Vestuario"), con la subcategoría
`shapewear` ("Vestimenta moldeadora") y tres conceptos: `faja_reductora`
(genérico), `faja_moldeadora_short` (tipo short sin costuras) y
`faja_moldeadora_colaless` (tipo colaless/tanga con cierre frontal).

A diferencia de las subcategorías que agregó `2026.2`, esta **no** viene del
puente `DomainTheme` ↔ `DomainConcept` (`app/nlp/dictionary.py`): la
vestimenta moldeadora/reductora es una línea de negocio aparte, sin relación
con geriatría, discapacidad o accesibilidad (confirmado con el usuario), así
que sus conceptos no tienen equivalente en `DomainTheme` — es la primera
excepción a esa identidad 1:1, y
`test_domain_themes_match_taxonomy_concepts_exactly` la deja explícita en vez
de exigir igualdad estricta.

Sus reglas de clasificación tampoco salen de `build_ruleset()`/`DomainDictionary`:
viven en `app/nlp/apparel_rules.py` (`build_apparel_ruleset()`), un ruleset
`Rule` construido a mano y sumado al motor en `ClassificationStageExecutor`
(`app/nlp/classification.py`). El capa semántica (`EmbeddingsStageExecutor`,
`build_concept_vectors`) sí toma los conceptos automáticamente porque itera la
`Taxonomy` completa, sin pasar por el diccionario.

## Ver también

- [`semantic-dictionary.md`](semantic-dictionary.md) — versionado del diccionario semántico, independiente de esta taxonomía.
- [`model-versioning.md`](model-versioning.md) — versionado de modelos entrenados.
