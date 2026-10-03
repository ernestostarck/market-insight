import json
from hashlib import sha256
from typing import Protocol

from app.domain.entities.raw_ingestion import RawIngestionEventRecord
from app.domain.ports.raw_ingestion_repository import RawIngestionRepository
from app.etl.models import IngestionRunContext, RawRecord, StoredRawRecord


class RawIngestor(Protocol):
    """Persists original payloads in staging without data loss."""

    def store(
        self,
        run: IngestionRunContext,
        records: list[RawRecord],
    ) -> list[StoredRawRecord]: ...


class InMemoryRawIngestor:
    """Simple ingestor used for tests and local architecture validation."""

    def __init__(self) -> None:
        self.items: list[StoredRawRecord] = []

    def store(
        self,
        run: IngestionRunContext,
        records: list[RawRecord],
    ) -> list[StoredRawRecord]:
        stored: list[StoredRawRecord] = []
        for record in records:
            payload_hash = sha256(
                json.dumps(record.payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            item = StoredRawRecord(
                source=record.source,
                resource=record.resource,
                source_id=record.source_id,
                payload=record.payload,
                payload_hash=payload_hash,
                received_at=record.extracted_at,
                ingestion_run_id=run.ingestion_run_id,
            )
            stored.append(item)
        self.items.extend(stored)
        return stored


class SqlAlchemyRawIngestor:
    """Persists raw records through the repository abstraction."""

    def __init__(self, repository: RawIngestionRepository) -> None:
        self._repository = repository

    def store(
        self,
        run: IngestionRunContext,
        records: list[RawRecord],
    ) -> list[StoredRawRecord]:
        entities = [
            RawIngestionEventRecord(
                id=None,
                ingestion_run_id=run.ingestion_run_id,
                source=record.source,
                resource=record.resource,
                source_id=record.source_id,
                payload=record.payload,
                payload_hash=_payload_hash(record.payload),
                metadata=record.metadata,
                received_at=record.extracted_at,
            )
            for record in records
        ]
        persisted = self._repository.add_many(entities)
        return [
            StoredRawRecord(
                source=item.source,
                resource=item.resource,
                source_id=item.source_id,
                payload=item.payload,
                payload_hash=item.payload_hash,
                received_at=item.received_at,
                ingestion_run_id=item.ingestion_run_id,
            )
            for item in persisted
        ]


def _payload_hash(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
