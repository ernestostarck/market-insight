# Text Preprocessing

`TextPreprocessor.preprocess()` (`app/nlp/preprocessing.py`) es el único punto
de entrada. Aplica los pasos siempre en el mismo orden — esto es lo que hace
al pipeline reproducible (mismo input -> mismo output), no un framework de
steps registrables:

```
None-coalesce -> HTML unescape+strip -> NFKC -> limpieza de corrupción/
caracteres invisibles -> limpieza de símbolos decorativos -> normalización
de abreviaciones -> normalización de unidades -> colapsar espacios ->
casefold -> detección de idioma
```

Cada paso es una función privada con test propio (`tests/nlp/test_preprocessing.py`).

## Corrección: no hay corrupción real en los datos de ChileCompra

Antes de implementar "limpieza de contenido corrupto" se verificó con la API
real de ChileCompra (licitación `1002588-89-LE26`) si el texto llegaba
corrupto — mensajes anteriores de esta sesión mostraban `Educaci�n`, `N�1` en
la salida de las tool calls. Se inspeccionaron los bytes crudos de la
respuesta HTTP y el string decodificado directamente:

```python
>>> chunk = raw_bytes[idx:idx+15]
b'Educaci\xc3\xb3n P\xc3\xbab'          # \xc3\xb3 es la codificación UTF-8 correcta de "ó"
>>> 'ó' in desc   # True
>>> '�' in desc   # False
```

El `�` era un artefacto de cómo la consola de Windows de esta sesión renderiza
acentos al mostrar la salida de las tool calls — el dato real, decodificado
directamente, es UTF-8 correcto. Por eso `_REPLACEMENT_CHAR`/`_INVISIBLE_CHARS`
en `preprocessing.py` son una **capacidad defensiva genérica** (para texto que
sí podría llegar corrupto de una fuente futura — OCR de documentos asociados,
copy-paste desde otro sistema) y no una respuesta a un problema observado. No
se agregó `ftfy` ni ninguna otra dependencia para esto — alcanza con manejo
defensivo de `U+FFFD` y caracteres invisibles usando solo stdlib.

## Normalización de abreviaciones — guardas de ambigüedad

`unicodedata.normalize("NFKC", ...)` (aplicado antes en el pipeline) convierte
"Nº" (U+00BA, ordinal masculino) en "No" (N + o normal) vía su descomposición
de compatibilidad — "N°" (U+00B0, signo de grado) no tiene descomposición y se
mantiene igual. Expandir "No" a "numero" sin cuidado corrompería negaciones
reales ("No aplica" -> "numero aplica"). La regla solo aplica cuando "N°"/
"Nº"/"No" está seguido inmediatamente de un dígito (`\bn\s*[o°]\s*(?=\d)`) —
sin ese contexto, no se toca. Verificado con dato real:
`"Línea N°1: Telas..."` -> `"linea numero 1: telas..."`.

## Normalización de unidades — misma cautela

`kg`, `mt`/`mts`, `lt`/`lts`, `m2`/`mt2` se normalizan sin guarda adicional
(no son palabras españolas comunes, seguro usar límites de palabra `\b`
solamente). `un`/`und`/`unid` sí colisionan con el artículo indefinido "un"
("un producto" = "a product") — por eso solo se tratan como la unidad
"unidad" cuando están directamente pegados a un número que los precede
(`10un`, `10 und.`, nunca como palabra suelta).

Ambas tablas son deliberadamente pequeñas y explícitas (dict/tupla + regex,
fácil de auditar). No se inventan abreviaciones sin justificación — 6.4
(Domain Dictionary) es quien agrega vocabulario semántico de dominio
(geriatría, discapacidad, etc.); esto es solo normalización superficial de
texto genérico.

## Tokenización

`tokenize(text: str) -> tuple[str, ...]` (`app/nlp/preprocessing.py`) es una
función standalone, no integrada al pipeline de `preprocess()` — nada la
consume todavía (`RuleEngine` hace matching de substring, no de tokens). Queda
disponible para cuando una fase futura (6.11 NER u otra) la necesite.

## Detección de idioma

Lista ampliada de marcadores + umbral proporcional: textos cortos (≤5
palabras, típico de un título) necesitan un solo marcador; textos más largos
necesitan que al menos 15% de las palabras sean marcadores. Se descartó
agregar `langdetect`/similar — el corpus es determinísticamente español
(licitaciones chilenas), una dependencia de ML es sobre-ingeniería para esto.

## Validación sobre datos reales

No hay un test que llame a la API real en la suite (dependencia de red =
flaky en CI). En su lugar, dos tests (`test_preprocess_on_real_licitacion_descripcion`,
`test_preprocess_on_real_item_descripcion_normalizes_numero`) usan como
fixtures literales textos reales ya confirmados en esta sesión — la
`Descripcion` de la licitación `1002588-89-LE26` y la descripción de uno de
sus ítems (con el patrón `N°1` real) — verificados contra el pipeline
completo.
