"""Entity extraction application service (Fase 6.18)."""

from __future__ import annotations

import uuid

from app.models.knowledge import Entity
from app.nlp.entities import ExtractedEntity, extract_text_entities
from app.repositories.knowledge import EntityRepository, RelationshipRepository


class EntityExtractionService:
    def __init__(
        self,
        entity_repository: EntityRepository | None = None,
        relationship_repository: RelationshipRepository | None = None,
    ) -> None:
        self._entity_repo = entity_repository
        self._relationship_repo = relationship_repository

    def extract_entities(
        self,
        text: str,
        *,
        organismo: str | None = None,
        items: list[str] | None = None,
        region: str | None = None,
        comuna: str | None = None,
    ) -> list[ExtractedEntity]:
        entities = list(extract_text_entities(text))
        if organismo:
            entities.append(
                ExtractedEntity(
                    entity_type="organismo",
                    value=organismo,
                    normalized_value=organismo.strip().lower(),
                    confidence_score=1.0,
                )
            )
        if region:
            entities.append(
                ExtractedEntity(
                    entity_type="region",
                    value=region,
                    normalized_value=region.strip().lower(),
                    confidence_score=1.0,
                )
            )
        if comuna:
            entities.append(
                ExtractedEntity(
                    entity_type="comuna",
                    value=comuna,
                    normalized_value=comuna.strip().lower(),
                    confidence_score=1.0,
                )
            )
        if items:
            for item in items:
                entities.append(
                    ExtractedEntity(
                        entity_type="producto",
                        value=item,
                        normalized_value=item.strip().lower(),
                        confidence_score=0.9,
                    )
                )
        return entities

    async def extract_and_store(
        self,
        licitacion_id: int,
        text: str,
        *,
        organismo: str | None = None,
        items: list[str] | None = None,
        classification_id: uuid.UUID | None = None,
    ) -> list[Entity]:
        extracted = self.extract_entities(text, organismo=organismo, items=items)
        db_entities = [
            Entity(
                id=uuid.uuid4(),
                licitacion_id=licitacion_id,
                classification_id=classification_id,
                entity_type=e.entity_type,
                value=e.value,
                normalized_value=e.normalized_value,
                confidence_score=e.confidence_score,
                start_offset=e.start_offset,
                end_offset=e.end_offset,
            )
            for e in extracted
        ]

        if self._entity_repo is not None and db_entities:
            db_entities = await self._entity_repo.create_many(db_entities)

        return db_entities
