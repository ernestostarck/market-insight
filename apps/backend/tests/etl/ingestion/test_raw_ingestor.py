from datetime import datetime, timezone

from app.domain.entities.raw_ingestion import RawIngestionEventRecord
from app.etl.ingestion.ingestion_run import new_ingestion_run
from app.etl.ingestion.raw_ingestor import SqlAlchemyRawIngestor
from app.etl.ingestion.staging_policy import StagingStoragePolicy
from app.etl.models import RawRecord


class FakeRawIngestionRepository:
    def __init__(self) -> None:
        self.saved: list[RawIngestionEventRecord] = []

    def add_many(
        self,
        entities: list[RawIngestionEventRecord],
    ) -> list[RawIngestionEventRecord]:
        persisted: list[RawIngestionEventRecord] = []
        for idx, entity in enumerate(entities, start=1):
            persisted.append(
                RawIngestionEventRecord(
                    id=idx,
                    ingestion_run_id=entity.ingestion_run_id,
                    source=entity.source,
                    resource=entity.resource,
                    source_id=entity.source_id,
                    payload=entity.payload,
                    payload_hash=entity.payload_hash,
                    metadata=entity.metadata,
                    received_at=entity.received_at,
                    created_at=datetime.now(timezone.utc),
                )
            )
        self.saved.extend(persisted)
        return persisted

    def list_by_run_id(
        self,
        ingestion_run_id: str,
    ) -> list[RawIngestionEventRecord]:
        return [
            item for item in self.saved if item.ingestion_run_id == ingestion_run_id
        ]

    def list_by_source_resource(
        self,
        *,
        source: str,
        resource: str,
        limit: int = 100,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
    ) -> list[RawIngestionEventRecord]:
        items = [
            item
            for item in self.saved
            if item.source == source and item.resource == resource
        ]
        if received_after is not None:
            items = [item for item in items if item.received_at >= received_after]
        if received_before is not None:
            items = [item for item in items if item.received_at <= received_before]
        items.sort(
            key=lambda item: (
                item.received_at or datetime.min.replace(tzinfo=timezone.utc),
                item.id or 0,
            ),
            reverse=True,
        )
        return items[:limit]


def test_sqlalchemy_raw_ingestor_stores_raw_records_with_hash() -> None:
    repository = FakeRawIngestionRepository()
    ingestor = SqlAlchemyRawIngestor(repository=repository)
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.3.0",
    )

    stored = ingestor.store(
        run=run,
        records=[
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="1000-1-LR26",
                payload={"CodigoExterno": "1000-1-LR26", "Estado": "ADJUDICADA"},
                extracted_at=datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc),
                metadata={"snapshot_date": "2026-08-06"},
            )
        ],
    )

    assert len(stored) == 1
    assert stored[0].ingestion_run_id == run.ingestion_run_id
    assert stored[0].source_id == "1000-1-LR26"
    assert len(stored[0].payload_hash) == 64

    persisted = repository.list_by_run_id(run.ingestion_run_id)
    assert len(persisted) == 1
    assert persisted[0].payload_hash == stored[0].payload_hash


def test_raw_repository_queries_by_source_resource_and_time_window() -> None:
    repository = FakeRawIngestionRepository()
    repository.saved = [
        RawIngestionEventRecord(
            id=1,
            ingestion_run_id="run-1",
            source="chilecompra_api",
            resource="licitaciones",
            source_id="1000-1-LR26",
            payload={"CodigoExterno": "1000-1-LR26"},
            payload_hash="a" * 64,
            metadata={},
            received_at=datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 8, 6, 12, 0, 1, tzinfo=timezone.utc),
        ),
        RawIngestionEventRecord(
            id=2,
            ingestion_run_id="run-2",
            source="open_data",
            resource="licitaciones_historicas",
            source_id="A-1",
            payload={"codigo": "A-1"},
            payload_hash="b" * 64,
            metadata={},
            received_at=datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 8, 5, 12, 0, 1, tzinfo=timezone.utc),
        ),
        RawIngestionEventRecord(
            id=3,
            ingestion_run_id="run-3",
            source="chilecompra_api",
            resource="licitaciones",
            source_id="1000-2-LR26",
            payload={"CodigoExterno": "1000-2-LR26"},
            payload_hash="c" * 64,
            metadata={},
            received_at=datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 8, 7, 12, 0, 1, tzinfo=timezone.utc),
        ),
    ]

    queried = repository.list_by_source_resource(
        source="chilecompra_api",
        resource="licitaciones",
        received_after=datetime(2026, 8, 6, 18, 0, 0, tzinfo=timezone.utc),
    )

    assert len(queried) == 1
    assert queried[0].ingestion_run_id == "run-3"


def test_staging_storage_policy_exposes_retention_and_partitioning() -> None:
    policy = StagingStoragePolicy(retention_days=30)
    reference = datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc)
    retained_record = datetime(2026, 7, 15, 9, 0, 0, tzinfo=timezone.utc)
    expired_record = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

    assert policy.retention_cutoff(reference) == datetime(
        2026, 7, 8, 10, 0, 0, tzinfo=timezone.utc
    )
    assert policy.partition_key(retained_record) == "2026_07"
    assert (
        policy.partition_table_name(retained_record) == "raw_ingestion_events_2026_07"
    )
    assert policy.is_expired(retained_record, reference) is False
    assert policy.is_expired(expired_record, reference) is True
