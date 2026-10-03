from datetime import datetime, timezone

from app.etl.error_handling.quarantine import InMemoryQuarantine
from app.etl.extraction.base import ExtractionWindow
from app.etl.ingestion.ingestion_run import new_ingestion_run
from app.etl.ingestion.raw_ingestor import InMemoryRawIngestor
from app.etl.loading.base import RecordLoader
from app.etl.models import (
    LoadResult,
    RawRecord,
    StoredRawRecord,
    TransformedRecord,
    ValidationResult,
)
from app.etl.orchestration.pipeline import ETLPipeline
from app.etl.transformation.base import RecordTransformer
from app.etl.validation.base import RecordValidator


class FakeSource:
    source_name = "chilecompra_api"

    async def extract(self, run, window: ExtractionWindow | None = None):
        _ = run
        _ = window
        now = datetime.now(timezone.utc)
        return [
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="1000-1-LR26",
                payload={"codigo": "1000-1-LR26", "estado": "ADJUDICADA"},
                extracted_at=now,
            ),
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="INVALID-1",
                payload={"codigo": "INVALID-1"},
                extracted_at=now,
            ),
        ]


class FakeValidator(RecordValidator):
    def validate(self, record: StoredRawRecord) -> ValidationResult:
        if "estado" not in record.payload:
            return ValidationResult(is_valid=False)
        return ValidationResult(
            is_valid=True,
            normalized_payload={
                "external_id": record.payload["codigo"],
                "status": record.payload["estado"].lower(),
            },
        )


class FakeTransformer(RecordTransformer):
    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        external_id = str(normalized_payload["external_id"])
        return TransformedRecord(
            entity="licitacion",
            natural_key=f"chilecompra:{external_id}",
            payload=normalized_payload,
            source_id=external_id,
            payload_hash="hash",
        )


class FakeLoader(RecordLoader):
    def __init__(self) -> None:
        self.loaded: list[TransformedRecord] = []

    def load(self, run, records):
        _ = run
        self.loaded.extend(records)
        return LoadResult(inserted=len(records))


async def test_etl_pipeline_preserves_raw_and_quarantine() -> None:
    pipeline = ETLPipeline(
        source=FakeSource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=FakeValidator(),
        transformer=FakeTransformer(),
        loader=FakeLoader(),
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.1.0",
    )

    summary = await pipeline.run(run=run)

    assert summary.metrics.extracted == 2
    assert summary.metrics.raw_stored == 2
    assert summary.metrics.valid == 1
    assert summary.metrics.invalid == 1
    assert summary.metrics.inserted == 1
    assert summary.quarantine_count == 1


class FakeValidatorWithIssues(RecordValidator):
    def validate(self, record: StoredRawRecord) -> ValidationResult:
        if "estado" not in record.payload:
            from app.etl.models import ValidationIssue

            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="missing_field",
                        message="Missing 'estado'",
                        field="estado",
                    )
                ],
            )
        return ValidationResult(
            is_valid=True,
            normalized_payload={
                "external_id": record.payload["codigo"],
                "status": record.payload["estado"].lower(),
            },
        )


class ExplodingTransformer(RecordTransformer):
    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        raise RuntimeError("transform exploded")


class ValidFakeSource:
    """Source that returns only records that pass validation."""

    source_name = "chilecompra_api"

    async def extract(self, run, window: ExtractionWindow | None = None):
        _ = run
        _ = window
        now = datetime.now(timezone.utc)
        return [
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="1000-1-LR26",
                payload={"codigo": "1000-1-LR26", "estado": "ADJUDICADA"},
                extracted_at=now,
            ),
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="1000-2-LR26",
                payload={"codigo": "1000-2-LR26", "estado": "PUBLICADA"},
                extracted_at=now,
            ),
        ]


async def test_etl_pipeline_quarantines_validation_failures() -> None:
    quarantine = InMemoryQuarantine()
    pipeline = ETLPipeline(
        source=FakeSource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=FakeValidatorWithIssues(),
        transformer=FakeTransformer(),
        loader=FakeLoader(),
        quarantine=quarantine,
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.12.0",
    )

    summary = await pipeline.run(run=run)

    assert summary.metrics.invalid == 1
    assert summary.quarantine_count == 1
    assert quarantine.count() == 1
    quarantined = quarantine.all()[0]
    assert quarantined.error_code == "missing_field"
    assert quarantined.source_id == "INVALID-1"
    assert quarantined.ingestion_run_id == run.ingestion_run_id
    assert quarantined.payload == {"codigo": "INVALID-1"}


async def test_etl_pipeline_quarantines_transform_errors() -> None:
    quarantine = InMemoryQuarantine()
    pipeline = ETLPipeline(
        source=ValidFakeSource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=FakeValidator(),
        transformer=ExplodingTransformer(),
        loader=FakeLoader(),
        quarantine=quarantine,
    )
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.12.0",
    )

    summary = await pipeline.run(run=run)

    # Both records pass validation, but both fail transformation,
    # so they are counted as invalid and quarantined.
    assert summary.metrics.valid == 0
    assert summary.metrics.invalid == 2
    assert summary.metrics.transformed == 0
    assert summary.quarantine_count == 2
    assert quarantine.count() == 2
    for record in quarantine.all():
        assert record.error_type == "transform_error"
        assert record.error_code == "RuntimeError"
        assert record.stack_trace is not None
