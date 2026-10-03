# Document Processing

`app/nlp/document.py` consolida el contenido textual de una licitación en un
`TenderDocument` (dataclass en memoria) y lo divide en `DocumentChunk`. La
estructura persistible correspondiente vive en `knowledge.documents` /
`knowledge.chunks` (`app/models/knowledge.py`, clases `Document`/`Chunk` —
migradas a Postgres en 6.6, ver `knowledge-layer.md`).

## Fuentes textuales: activas vs. N/A

| Fuente | Estado | Detalle |
| --- | --- | --- |
| Nombre de la licitación | **Activa** | `core.Licitacion.nombre`, poblado por el sync diario del ETL (endpoint de listado). |
| Descripción | **Activa** | `core.Licitacion.descripcion` — poblada por el enriquecimiento bajo demanda (`app/etl/enrichment/licitacion_detail.py`), no por el sync diario (el listado no la trae). |
| Ítems | **Activa (bajo demanda)** | `core.LicitacionItem` se puebla vía `enrich_licitacion_detail(codigo)` (`app/etl/orchestration/jobs.py`), que llama al endpoint de detalle de ChileCompra (`por_codigo`) y hace upsert de `Items.Listado[]`. No se ejecuta en el sync diario (~1000+ licitaciones/día encarecería demasiado la llamada a la API) — se dispara una licitación a la vez, típicamente antes de construir su `TenderDocument`. `producto_id`/`categoria_id` quedan `NULL` — no hay catálogo UNSPSC todavía para resolverlos. |
| Especificaciones técnicas | **N/A** | Confirmado con la API real: no existe como campo, ni en el listado ni en el detalle (46 claves de nivel superior revisadas, ninguna coincide). No es "falta código" — ChileCompra no lo entrega. Cerrado, no bloqueado: no hay nada que desbloquear. |
| Observaciones | **N/A** | Existe `ObservacionContract` en el detalle, pero es específico de contrato (no de la licitación en general) y venía `null` en la muestra revisada — no cubre lo que TODO.md asume como "observaciones" de la licitación. Cerrado por la misma razón. |
| Documentos asociados | **N/A** | Confirmado con la API real, licitación 1002588-89-LE26: el payload de detalle (46 claves de nivel superior) no tiene ningún campo de documentos/anexos/archivos — ChileCompra no expone attachments en la API pública, ni siquiera como metadata (nombre/url). `core.Documento` (nombre, tipo, url, checksum — bases, anexos, ofertas) queda como modelo canónico genérico sin fuente de ChileCompra que lo pueble; no se justifica construir extracción de texto/OCR para una fuente que no existe. No confundir con `app.models.document_metadata.DocumentMetadata`, que es almacenamiento de archivos subidos por el propio sistema (bucket/checksum en MinIO), un concepto distinto. |

`build_document` (`app/nlp/document.py`) reutiliza directamente
`TextPreprocessor.build_tender_document(title, description, item_texts)`
(`app/nlp/preprocessing.py`), que ya acepta `item_texts` — una vez que
`enrich_licitacion_detail` corrió para una licitación y `core.LicitacionItem`
tiene filas, el caller solo necesita pasarle esos textos; la función no
cambia.

### Cómo se dispara el enriquecimiento bajo demanda

`enrich_licitacion_detail` (task de Celery, `app/etl/orchestration/jobs.py`)
no está en `celery beat` — se despacha explícitamente
(`enrich_licitacion_detail.delay(codigo)`) para una licitación a la vez.
Reutiliza `CoreLicitacionLoader.load()` (mismo camino de upsert/dedupe que el
sync diario) para `descripcion`/organismo/fechas, y `CoreLicitacionItemLoader`
para los ítems. Hoy no existe todavía el punto de integración que decida
*cuándo* llamarlo automáticamente (ej. "antes de construir un Document para
NLP") — eso depende de 6.19/6.21, que no existen aún; por ahora es una
capacidad invocable, no un flujo automático.

## Estructura

- `TenderDocument`: `licitacion_id`, `raw_text` (texto original concatenado),
  `normalized_text`, `language`, `content_hash`, `chunks`. `raw_text`/
  `normalized_text` mantienen la trazabilidad entre el texto original y el
  procesado.
- `DocumentChunk`: `sequence`, `text`, `start_offset`, `end_offset` — offsets
  de caracter dentro de `normalized_text`, mismo concepto que ya usan
  `Entity.start_offset`/`end_offset` en `knowledge.entities`.
- `TextChunker`: divide `normalized_text` en oraciones (por `.`/`!`/`?` +
  espacio) y las acumula sin exceder `max_chars`, sin cortar nunca una
  palabra a la mitad — incluso si una sola oración sin puntuación excede el
  límite, cae a un corte por límites de palabra. Con las fuentes activas de
  hoy (nombre + descripción, típicamente cortos) casi siempre produce un solo
  chunk; la estrategia existe completa para cuando una fuente larga
  (documentos asociados) se desbloquee.

## Persistencia idempotente

`Document` tiene un `UniqueConstraint(licitacion_id, content_hash)`: reprocesar
una licitación cuyo texto no cambió no crea una fila duplicada; si el texto
cambia, se crea un `Document` nuevo — el mismo principio de "nunca mutar una
ejecución histórica" que ya usan `Classification`/`ModelVersion`/`Keyword`
(ver `model-versioning.md`).

## Conexión con el job asíncrono

`NLPJobRequest.text_hash` (`app/nlp/contracts.py`, de 6.1) no lo produce nada
en el código todavía — hoy es solo un campo de entrada esperado.
`TenderDocument.content_hash` es exactamente el valor que debe alimentarlo:
quien someta un job para una licitación debe construir primero su
`TenderDocument` y usar su `content_hash` como `text_hash`. Esta conexión
queda documentada aquí; el flujo end-to-end (construir el documento, someter
el job, persistir `Document`/`Chunk`) se conecta en una fase posterior
(6.19 NLP Repository Layer / 6.21 NLP API), no en 6.2.
