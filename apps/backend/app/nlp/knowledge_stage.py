"""KNOWLEDGE stage executor: NER (6.11) + product/attribute extraction
(6.12) -> persisted `knowledge.entities` / `knowledge.products`.

The last of the 3 async stages (classification -> embeddings -> knowledge,
docs/07-ai/architecture.md) — 6.12 adds to this stage rather than
introducing a 4th, since it already loads core.licitacion_item per
licitacion for the same reason (6.11's 'producto' entity). Same Core
(Connection + text()) style as ClassificationStageExecutor/
EmbeddingsStageExecutor.

organismo/ubicacion/producto are projections of already-known structured
data (core.organismo, core.licitacion_item) — not text-mined — so they
carry confidence_score=1.0 and no offsets. Only cantidad/unidad/fecha/
monto/marca/modelo genuinely come from reading normalized_text (see
app/nlp/entities.py).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.dictionary import DomainDictionary, load_initial_dictionary
from app.nlp.entities import extract_text_entities
from app.nlp.product_attributes import extract_product_attributes
from app.nlp.product_concepts import match_product_concepts
from app.nlp.product_taxonomy_db import resolve_product_concept
from app.nlp.stages import StageContext
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_db import resolve_category, resolve_subcategory

logger = logging.getLogger(__name__)

_STRUCTURED_CONFIDENCE = 1.0
_PRODUCT_MATCH_CONFIDENCE = 1.0


class KnowledgeStageExecutor:
    def __init__(
        self,
        connection_factory: Callable[[], Connection],
        dictionary: DomainDictionary | None = None,
        taxonomy: Taxonomy | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._dictionary = dictionary or load_initial_dictionary()
        self._taxonomy = taxonomy or load_initial_taxonomy()

    def run(self, context: StageContext) -> bool:
        connection = self._connection_factory()
        try:
            document = connection.execute(
                text(
                    "SELECT normalized_text FROM knowledge.documents "
                    "WHERE licitacion_id = :licitacion_id AND content_hash = :content_hash"
                ),
                {"licitacion_id": context.licitacion_id, "content_hash": context.text_hash},
            ).first()
            if document is None:
                logger.warning(
                    "No preprocessed document for licitacion_id=%s content_hash=%s",
                    context.licitacion_id, context.text_hash,
                )
                return False

            classification_id = self._latest_classification_id(connection, context)
            items = connection.execute(
                text(
                    "SELECT id, nombre, descripcion, cantidad, unidad FROM core.licitacion_item "
                    "WHERE licitacion_id = :licitacion_id"
                ),
                {"licitacion_id": context.licitacion_id},
            ).all()

            rows: list[dict] = []
            rows.extend(self._structured_rows(connection, context.licitacion_id, classification_id, items))
            for entity in extract_text_entities(document[0]):
                rows.append({
                    "id": uuid.uuid4(), "licitacion_id": context.licitacion_id,
                    "classification_id": classification_id, "entity_type": entity.entity_type,
                    "value": entity.value, "normalized_value": entity.normalized_value,
                    "confidence_score": entity.confidence_score,
                    "start_offset": entity.start_offset, "end_offset": entity.end_offset,
                })

            for row in rows:
                connection.execute(
                    text(
                        "INSERT INTO knowledge.entities "
                        "(id, licitacion_id, classification_id, entity_type, value, normalized_value, "
                        "confidence_score, start_offset, end_offset) "
                        "VALUES (:id, :licitacion_id, :classification_id, :entity_type, :value, "
                        ":normalized_value, :confidence_score, :start_offset, :end_offset)"
                    ),
                    row,
                )

            self._persist_products(connection, context.licitacion_id, classification_id, items)

            connection.commit()
            return True
        except Exception:
            logger.exception("knowledge stage failed for licitacion_id=%s", context.licitacion_id)
            connection.rollback()
            return False
        finally:
            connection.close()

    def _latest_classification_id(self, connection: Connection, context: StageContext) -> uuid.UUID | None:
        row = connection.execute(
            text(
                "SELECT id FROM knowledge.classifications "
                "WHERE licitacion_id = :licitacion_id AND taxonomy_version = :taxonomy_version "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"licitacion_id": context.licitacion_id, "taxonomy_version": context.versions.taxonomy},
        ).first()
        return row[0] if row is not None else None

    def _structured_rows(
        self, connection: Connection, licitacion_id: int, classification_id: uuid.UUID | None, items: list,
    ) -> list[dict]:
        rows: list[dict] = []

        organismo = connection.execute(
            text(
                "SELECT o.nombre, o.region, o.comuna FROM core.licitacion l "
                "JOIN core.organismo o ON o.id = l.organismo_id WHERE l.id = :licitacion_id"
            ),
            {"licitacion_id": licitacion_id},
        ).first()
        if organismo is not None:
            nombre, region, comuna = organismo
            if nombre:
                rows.append(self._structured_row(licitacion_id, classification_id, "organismo", nombre))
            ubicacion = ", ".join(part for part in (comuna, region) if part)
            if ubicacion:
                rows.append(self._structured_row(licitacion_id, classification_id, "ubicacion", ubicacion))

        for item in items:
            _, nombre, _, _, _ = item
            if nombre:
                rows.append(self._structured_row(licitacion_id, classification_id, "producto", nombre))

        return rows

    def _persist_products(
        self, connection: Connection, licitacion_id: int, classification_id: uuid.UUID | None, items: list,
    ) -> None:
        for item in items:
            item_id, nombre, descripcion, cantidad, unidad = item
            item_text = " ".join(part for part in (nombre, descripcion) if part)
            if not item_text:
                continue
            for match in match_product_concepts(item_text, self._dictionary):
                category_id = resolve_category(connection, self._taxonomy, match.category_code)
                subcategory_id = resolve_subcategory(
                    connection, self._taxonomy, category_id, match.category_code, match.subcategory_code,
                )
                product_concept_id = resolve_product_concept(
                    connection, self._dictionary, match.concept_code, category_id, subcategory_id,
                )
                attributes = extract_product_attributes(item_text)
                connection.execute(
                    text(
                        "INSERT INTO knowledge.products "
                        "(id, licitacion_id, licitacion_item_id, product_concept_id, classification_id, "
                        "cantidad, unidad, materiales, dimensiones, capacidad, caracteristicas_tecnicas, "
                        "confidence_score) "
                        "VALUES (:id, :licitacion_id, :licitacion_item_id, :product_concept_id, "
                        ":classification_id, :cantidad, :unidad, :materiales, :dimensiones, :capacidad, "
                        ":caracteristicas_tecnicas, :confidence_score) "
                        "ON CONFLICT (licitacion_item_id, product_concept_id) DO NOTHING"
                    ),
                    {
                        "id": uuid.uuid4(), "licitacion_id": licitacion_id, "licitacion_item_id": item_id,
                        "product_concept_id": product_concept_id, "classification_id": classification_id,
                        "cantidad": cantidad, "unidad": unidad,
                        "materiales": json.dumps(list(attributes.materiales)),
                        "dimensiones": attributes.dimensiones, "capacidad": attributes.capacidad,
                        "caracteristicas_tecnicas": json.dumps(list(attributes.caracteristicas_tecnicas)),
                        "confidence_score": _PRODUCT_MATCH_CONFIDENCE,
                    },
                )

    @staticmethod
    def _structured_row(
        licitacion_id: int, classification_id: uuid.UUID | None, entity_type: str, value: str,
    ) -> dict:
        return {
            "id": uuid.uuid4(), "licitacion_id": licitacion_id, "classification_id": classification_id,
            "entity_type": entity_type, "value": value, "normalized_value": None,
            "confidence_score": _STRUCTURED_CONFIDENCE, "start_offset": None, "end_offset": None,
        }
