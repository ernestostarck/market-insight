"""End-to-end ETL tests (Fase 3.14).

These tests exercise the full pipeline wiring with fakes: extract -> raw
storage -> validation -> transformation -> dedup -> load, and additionally
drive the incremental engine with an audit reporter so the audit trail is
verified end to end.

They deliberately avoid a live database / network; they use protocol-based
fakes so the whole architecture is validated quickly and deterministically.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.etl.audit.reporter import InMemoryAuditReporter
from app.etl.error_handling.quarantine import InMemoryQuarantine
from app.etl.extraction.base import ExtractionWindow
from app.etl.incremental.engine import IncrementalETL
from app.etl.incremental.models import IncrementalRunStatus
from app.etl.incremental.window import IncrementalPlanner
from app.etl.ingestion.raw_ingestor import InMemoryRawIngestor
from app.etl.loading.base import RecordLoader
from app.etl.models import (
    ETLMetrics,
    ETLRunSummary,
    LoadResult,
    RawRecord,
    StoredRawRecord,
    TransformedRecord,
    ValidationResult,
)
from app.etl.orchestration.pipeline import ETLPipeline
from app.etl.quality.base import QualityReporter
from app.etl.transformation.base import RecordTransformer
from app.etl.validation.base import RecordValidator


class E2ESource:
    """Emits a handful of raw licitaciones records (one invalid)."""

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
                payload={"CodigoExterno": "1000-1-LR26", "Estado": "Adjudicada"},
                extracted_at=now,
            ),
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="1000-2-LR26",
                payload={"CodigoExterno": "1000-2-LR26", "Estado": "Publicada"},
                extracted_at=now,
            ),
            RawRecord(
                source="chilecompra_api",
                resource="licitaciones",
                source_id="INVALID-1",
                payload={"CodigoExterno": "INVALID-1"},
                extracted_at=now,
            ),
        ]


class E2EValidator(RecordValidator):
    def validate(self, record: StoredRawRecord) -> ValidationResult:
        if "Estado" not in record.payload:
            from app.etl.models import ValidationIssue

            return ValidationResult(
                is_valid=False,
                issues=[
                    ValidationIssue(
                        code="missing_estado",
                        message="Missing Estado",
                        field="Estado",
                    )
                ],
            )
        return ValidationResult(
            is_valid=True,
            normalized_payload={
                "external_id": record.payload["CodigoExterno"],
                "title": record.payload["CodigoExterno"],
                "status": record.payload["Estado"].upper(),
            },
        )


class E2ETransformer(RecordTransformer):
    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        external_id = str(normalized_payload["external_id"])
        status = str(normalized_payload["status"])
        if status == "ADJUDICADA":
            raise RuntimeError("boom on adjudicada")
        return TransformedRecord(
            entity="licitaciones",
            natural_key=f"chilecompra:{external_id}",
            payload=normalized_payload,
            source_id=external_id,
            payload_hash="hash-" + external_id,
        )


class E2ELoader(RecordLoader):
    def __init__(self) -> None:
        self.loaded: list[TransformedRecord] = []

    def load(self, run, records):
        _ = run
        self.loaded.extend(records)
        return LoadResult(inserted=len(records))


class E2EQualityReporter(QualityReporter):
    def __init__(self) -> None:
        self.reports = []

    def emit(self, run, metrics: ETLMetrics) -> None:
        self.reports.append((run, metrics))


def _build_pipeline(
    *,
    quarantine: InMemoryQuarantine | None = None,
    quality: E2EQualityReporter | None = None,
) -> ETLPipeline:
    return ETLPipeline(
        source=E2ESource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=E2EValidator(),
        transformer=E2ETransformer(),
        loader=E2ELoader(),
        quality_reporter=quality,
        quarantine=quarantine,
    )


async def test_end_to_end_full_pipeline_flow() -> None:
    from datetime import timezone
    from uuid import uuid4

    from app.etl.ingestion.ingestion_run import new_ingestion_run

    quarantine = InMemoryQuarantine()
    quality = E2EQualityReporter()
    pipeline = _build_pipeline(quarantine=quarantine, quality=quality)
    run = new_ingestion_run(
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="3.14.0",
    )

    summary = await pipeline.run(run=run)

    # 3 extracted, 3 raw stored.
    assert summary.metrics.extracted == 3
    assert summary.metrics.raw_stored == 3

    # 2 pass validation, 1 fails validation (quarantined).
    # 1 of the 2 valid ones fails transformation (adjudicada) -> also invalid.
    # So: valid=1, invalid=2, transformed=1, quarantine=2.
    assert summary.metrics.valid == 1
    assert summary.metrics.invalid == 2
    assert summary.metrics.transformed == 1
    assert summary.metrics.inserted == 1
    assert summary.quarantine_count == 2
    assert quarantine.count() == 2

    # One validation-failure and one transform-error quarantined records.
    error_codes = {r.error_code for r in quarantine.all()}
    assert "missing_estado" in error_codes
    assert "RuntimeError" in error_codes

    # Quality reporter emitted once.
    assert len(quality.reports) == 1
    _, metrics = quality.reports[0]
    assert metrics.valid == 1
    assert metrics.invalid == 2


class IncrementalPipeline:
    """Pipeline used by the incremental engine in the e2e test."""

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, *, run, window: ExtractionWindow | None = None):
        self.calls += 1
        metrics = ETLMetrics(extracted=5, valid=4, invalid=1, inserted=4)
        return ETLRunSummary(run=run, metrics=metrics, quarantine_count=1)


async def test_end_to_end_incremental_engine_emits_audit_on_success() -> None:
    from datetime import date

    from app.etl.incremental.checkpointer import InMemoryCheckpointStore

    audit = InMemoryAuditReporter()
    store = InMemoryCheckpointStore()
    pipeline = IncrementalPipeline()
    engine = IncrementalETL(
        pipeline_factory=lambda: pipeline,
        checkpointer=store,
        planner=IncrementalPlanner(backfill_chunk_days=30),
        resource="licitaciones",
        source="chilecompra_api",
        audit_reporter=audit,
    )

    run = await engine.run(
        history_start=date(2026, 1, 1),
        end_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )

    assert run.status == IncrementalRunStatus.SUCCEEDED
    assert audit.count() == 1
    record = audit.last
    assert record is not None
    assert record.ingestion_run_id == run.run_id
    assert record.source == "chilecompra_api"
    assert record.resource == "licitaciones"
    assert record.endpoint == "/licitaciones.json"
    assert record.status.value == "succeeded"
    assert record.extracted >= 5
    assert record.valid >= 4
    assert record.invalid >= 1
    assert record.duration_ms is not None


async def test_end_to_end_incremental_engine_emits_audit_on_failure() -> None:
    from app.etl.incremental.checkpointer import InMemoryCheckpointStore

    audit = InMemoryAuditReporter()
    engine = IncrementalETL(
        pipeline_factory=_exploding_pipeline,
        checkpointer=InMemoryCheckpointStore(),
        resource="ordenes_compra",
        source="chilecompra_api",
        audit_reporter=audit,
    )

    run = await engine.run(end_at=datetime(2026, 8, 6, tzinfo=timezone.utc))

    assert run.status == IncrementalRunStatus.FAILED
    assert audit.count() == 1
    record = audit.last
    assert record is not None
    assert record.status.value == "failed"
    assert record.error is not None
    assert record.resource == "ordenes_compra"


def _exploding_pipeline():
    class ExplodingPipeline:
        async def run(self, *, run, window: ExtractionWindow | None = None):
            raise RuntimeError("pipeline exploded")

    return ExplodingPipeline()
