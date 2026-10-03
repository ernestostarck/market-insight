# Named Entity Recognition (NER)

Tercer y último stage real del pipeline asíncrono
(`PipelineStage.KNOWLEDGE`, `KnowledgeStageExecutor` en `STAGE_REGISTRY`,
`app/worker/nlp_tasks.py`) — con esta fase, `classification -> embeddings
-> knowledge` queda completo por primera vez (los 3 stages registrados).

## Las 9 entidades y su fuente

`organismo`/`ubicacion`/`producto` **no se extraen del texto** — ya están
estructurados. Extraerlos vía NLP sería reinventar con menor certeza algo
que ya se conoce con exactitud:

| `entity_type` | Fuente | `confidence_score` | offsets |
| --- | --- | --- | --- |
| `organismo` | `core.organismo.nombre` (FK desde `core.licitacion`) | 1.0 | no |
| `ubicacion` | `core.organismo.region`/`comuna` (si existen) | 1.0 | no |
| `producto` | `core.licitacion_item.nombre` (uno por ítem, ya poblado por 6.2) | 1.0 | no |
| `cantidad` | regex sobre `normalized_text` | 0.9 | sí |
| `unidad` | idem — mismo vocabulario que 6.3 (kg/m/m2/l/unidad) | 0.9 | sí |
| `fecha` | regex (numérica DD/MM/AAAA y "d de MES de AAAA") | 0.9 | sí |
| `monto` | regex (`$...`, "pesos", "UF", "UTM") | 0.9 | sí |
| `marca` | regex, solo tras la palabra "marca" explícita | 0.6 | sí |
| `modelo` | regex, solo tras la palabra "modelo" explícita | 0.6 | sí |

`app/nlp/entities.py` implementa las 6 últimas (`extract_text_entities`);
`app/nlp/knowledge_stage.py` proyecta las 3 primeras directo desde SQL.

## Por qué marca/modelo son deliberadamente de baja cobertura

Se decidió con el usuario **no** usar heurísticas de capitalización
("secuencias de palabras con mayúscula inicial") para detectar marcas —
sin un gold dataset (6.13) para medir precisión real, ese tipo de regla
genera muchos falsos positivos sobre texto real de licitaciones chilenas
(nombres propios de organismos, siglas, títulos de ítems, todo capitalizado
también). Se optó por alta precisión y baja cobertura: solo dispara sobre
"marca"/"modelo" explícitos en el texto — un patrón real y común en pliegos
técnicos chilenos — con `confidence_score = 0.6`, más bajo que el resto,
para que quede claro que es best-effort.

## Dos bugs reales encontrados validando con datos reales

1. **`\bmarca` sin `\b` de cierre** hacía match dentro de "marcas" (plural)
   — misma clase de bug que el de "to" en 6.7 (substring sin límite de
   palabra completo). Regresión:
   `tests/nlp/test_entities.py::test_marca_does_not_match_the_plural_marcas`.
2. **La captura de marca/modelo cruzaba puntuación**: "modelo Action 3,
   presupuesto referencial" capturaba "Action 3, presupuesto" en vez de
   solo "Action 3" — el patrón `\S+` no excluía comas. Se cambió a
   `[\w-]+` (solo caracteres de palabra y guión), que naturalmente detiene
   la captura en la puntuación. Regresión:
   `test_modelo_capture_stops_at_punctuation`.
3. **Montos arrastraban una coma de puntuación**: `"$1.500.000,"` en vez
   de `"$1.500.000"` — el patrón `[\d.,]+` no distinguía el punto/coma de
   separador de miles del de puntuación de oración. Se corrigió exigiendo
   que el match termine en un dígito. Regresión:
   `test_monto_does_not_swallow_a_trailing_sentence_comma`.

## `KnowledgeStageExecutor` (`app/nlp/knowledge_stage.py`)

Mismo estilo Core (`Connection`+`text()`) que `ClassificationStageExecutor`/
`EmbeddingsStageExecutor`. Busca `knowledge.documents` por
`(licitacion_id, content_hash)` (sin documento, `return False`), arma las
entidades estructuradas + las de texto, resuelve la `knowledge.classifications`
más reciente para enlazar `classification_id` (nullable — puede no existir
si `CLASSIFICATION` no corrió aún o no hizo match), inserta todo en
`knowledge.entities`, `commit()`. Cero entidades encontradas (ni ítems, ni
región/comuna, ni matches de regex) es un resultado válido, no una falla.

## Validado con datos reales

Contra Postgres dev real: licitación con organismo (con región/comuna), 2
ítems, y texto con "50 kg", "marca Invacare modelo Action 3", "$1.500.000",
"15/03/2026" — las 10 entidades esperadas se persistieron correctamente
(2 `producto`, 1 cada uno del resto), con `classification_id` enlazado a la
clasificación de 6.7 corrida sobre la misma licitación. Limpieza al final,
sin datos de prueba dejados.

## Fuera de alcance (explícito)

- Extracción de producto/atributos desde texto libre (materiales,
  dimensiones, capacidades, características técnicas) — 6.12 completo.
- Heurísticas de marca/modelo por capitalización — descartado
  explícitamente, ver arriba.
- Ubicaciones mencionadas en el texto libre (ej. dirección de entrega)
  distintas de la región/comuna del organismo — sin fuente estructurada
  ni gazetteer, queda para una fase futura si hace falta.

## Ver también

- [`document-processing.md`](document-processing.md) — de dónde sale `normalized_text`.
- [`rule-classification.md`](rule-classification.md) — `CLASSIFICATION`, el stage anterior.
- [`architecture.md`](architecture.md) — orden del pipeline; con esta fase quedan los 3 stages async registrados.
