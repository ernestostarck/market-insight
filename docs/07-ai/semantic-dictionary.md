# Versionado del diccionario semántico

El diccionario semántico (`knowledge.keywords`) es un artefacto versionado de
forma independiente a la taxonomía. `ArtifactVersions.semantic_dictionary`
(`app/nlp/contracts.py`) lo trata como un campo propio, distinto de
`ArtifactVersions.taxonomy` — un job NLP puede combinar cualquier
`dictionary_version` con cualquier `taxonomy_version` compatible.

Los códigos de versión siguen el formato `dictionary-<label>`, por ejemplo
`dictionary-2026.1`. `DictionaryVersion` (`app/nlp/contracts.py`) valida ese
prefijo — es un tipo de validación opt-in; los campos de transporte
(`ArtifactVersions.semantic_dictionary`, `NLPJobCreate.dictionary_version`)
siguen siendo `str` planos para no romper la compatibilidad de payload ni el
`idempotency_key`.

## Invariante append-only

Igual que la taxonomía (`taxonomy.md`), un término ya publicado bajo una
versión nunca se repunta a otra categoría: para cambiar un mapeo término→
categoría se publica una `dictionary_version` nueva. Las filas de
`knowledge.keywords` de una versión anterior no se modifican ni se borran.

## Independencia de `taxonomy_version`

Una release del diccionario puede apuntar a una `taxonomy_version` existente
sin cambiarla. Cuando se publica una `taxonomy_version` nueva (`taxonomy.md`),
los mapeos del diccionario deben re-revisarse antes de promoverlos para esa
taxonomía — una nueva categoría no tiene automáticamente términos asociados.

## Cómo queda scoped `knowledge.keywords`

Cada fila de `Keyword` (`app/models/knowledge.py`) lleva `taxonomy_version` y
`dictionary_version` como columnas independientes, unidas en el constraint
`uq_knowledge_keywords_scope` junto con `term`, `category_id` y
`subcategory_id`. Esto permite que el mismo término participe en distintas
versiones del diccionario sin colisionar, y que una consulta pueda filtrar por
ambas versiones a la vez — el mismo patrón "versión como columna, sin tabla de
versión aparte" que ya usa `Category`/`Subcategory` con `taxonomy_version`.

## Estructura y contenido (6.4)

`load_initial_dictionary()` (`app/nlp/dictionary.py`) sigue el mismo patrón
que `load_initial_taxonomy()`: lee `app/nlp/data/dictionary-2026.1.json` vía
`importlib.resources`, valida y devuelve un `DomainDictionary` (dataclass
inmutable, sin persistencia — igual que `Taxonomy`, no escribe a la base de
datos; eso es 6.6/6.7).

Cada `DictionaryEntry` tiene `concept` (id estable), `theme` (uno de 9
`DomainTheme`), `term` (forma canónica), `synonyms`, `abbreviations`,
y opcionalmente `category_code`/`subcategory_code`.

### Por qué la mayoría de los términos no tienen categoría

Los 9 temas requeridos (geriatría, adultos mayores, discapacidad, movilidad
reducida, accesibilidad, ayudas técnicas, prevención de caídas,
rehabilitación, adaptación de espacios) son **poblaciones/temas
transversales**, no categorías de producto — la taxonomía actual
(`taxonomy-2026.1`, `docs/07-ai/taxonomy.md`) tiene 6 sectores genéricos
(tecnología, salud, construcción, transporte, servicios profesionales,
suministros generales) que no los cubren 1:1. Una silla de ruedas es a la vez
"salud/equipamiento-médico" y "discapacidad"; una rampa es a la vez
"construcción/obras-civiles" y "accesibilidad". Por diseño (confirmado con el
usuario), la mayoría de las entradas quedan **sin** `category_id`/
`subcategory_id` — son señales de relevancia para 6.16 (Market Relevance), no
clasificadores de producto — y solo se asocian a una categoría existente
cuando el fit es genuinamente obvio (equipamiento médico, obras civiles).
`DomainDictionary.validate(taxonomy)` verifica que todo `category_code`/
`subcategory_code` usado exista de verdad en la taxonomía real, para detectar
drift entre los dos artefactos versionados.

### Cobertura de los 9 temas (`dictionary-2026.1`)

| Tema | Ejemplos |
| --- | --- |
| `geriatria` | geriatría, gerontología |
| `adultos_mayores` | adulto mayor, centro de día, ELEAM |
| `discapacidad` | discapacidad (PcD), visual, auditiva, motora, intelectual |
| `movilidad_reducida` | silla de ruedas, andador, bastón, muletas |
| `accesibilidad` | rampa de acceso, ascensor accesible, baño accesible, señalética braille |
| `ayudas_tecnicas` | audífono, prótesis, órtesis, grúa de traslado |
| `prevencion_caidas` | barra de apoyo, piso antideslizante |
| `rehabilitacion` | kinesiología (kine), terapia ocupacional (TO), fonoaudiología |
| `adaptacion_espacios` | ampliación de vanos de puertas, eliminación de barreras arquitectónicas |

Nota: la vestimenta moldeadora/reductora (fajas tipo body) es una línea de
negocio aparte, sin relación con estos 9 temas — no vive en este diccionario.
Ver `taxonomy.md` (categoría `apparel`) y `app/nlp/apparel_rules.py`.

`DomainDictionary.validate()` exige que los 9 temas tengan al menos una
entrada — si falta uno, la carga falla en vez de quedar silenciosamente
incompleta.
