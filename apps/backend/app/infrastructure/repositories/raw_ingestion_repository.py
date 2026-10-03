from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.raw_ingestion import RawIngestionEventRecord
from app.domain.ports.raw_ingestion_repository import RawIngestionRepository
from app.models.raw_ingestion_event import RawIngestionEvent


class SqlAlchemyRawIngestionRepository(RawIngestionRepository):
    """SQLAlchemy repository for staging raw ingestion events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(
        self,
        entities: list[RawIngestionEventRecord],
    ) -> list[RawIngestionEventRecord]:
        models = [
            RawIngestionEvent(
                ingestion_run_id=entity.ingestion_run_id,
                source=entity.source,
                resource=entity.resource,
                source_id=entity.source_id,
                payload=entity.payload,
                payload_hash=entity.payload_hash,
                metadata_json=entity.metadata or {},
                received_at=entity.received_at,
            )
            for entity in entities
        ]
        self._session.add_all(models)
        self._session.commit()
        for model in models:
            self._session.refresh(model)
        return [self._to_record(model) for model in models]

    def list_by_run_id(
        self,
        ingestion_run_id: str,
    ) -> Iterable[RawIngestionEventRecord]:
        models = self._session.scalars(
            select(RawIngestionEvent)
            .where(RawIngestionEvent.ingestion_run_id == ingestion_run_id)
            .order_by(RawIngestionEvent.id.asc())
        ).all()
        return [self._to_record(model) for model in models]

    def list_by_source_resource(
        self,
        *,
        source: str,
        resource: str,
        limit: int = 100,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
    ) -> Iterable[RawIngestionEventRecord]:
        statement = (
            select(RawIngestionEvent)
            .where(RawIngestionEvent.source == source)
            .where(RawIngestionEvent.resource == resource)
        )
        if received_after is not None:
            statement = statement.where(RawIngestionEvent.received_at >= received_after)
        if received_before is not None:
            statement = statement.where(
                RawIngestionEvent.received_at <= received_before
            )

        models = self._session.scalars(
            statement.order_by(RawIngestionEvent.received_at.desc())
            .order_by(RawIngestionEvent.id.desc())
            .limit(limit)
        ).all()
        return [self._to_record(model) for model in models]

    @staticmethod
    def _to_record(model: RawIngestionEvent) -> RawIngestionEventRecord:
        return RawIngestionEventRecord(
            id=model.id,
            ingestion_run_id=model.ingestion_run_id,
            source=model.source,
            resource=model.resource,
            source_id=model.source_id,
            payload=model.payload,
            payload_hash=model.payload_hash,
            metadata=model.metadata_json,
            received_at=model.received_at,
            created_at=model.created_at,
        )
