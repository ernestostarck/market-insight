from __future__ import annotations

from datetime import datetime, timezone

import pytest
from app.etl.extraction.base import ExtractionWindow
from app.etl.ingestion.raw_ingestor import InMemoryRawIngestor
from app.etl.loading.base import RecordLoader
from app.etl.models import (
    ETLMetrics,
    IngestionRunContext,
    LoadResult,
    RawRecord,
    StoredRawRecord,
    TransformedRecord,
    ValidationResult,
)
from app.etl.orchestration.pipeline import ETLPipeline
from app.etl.quality.metrics import QualityMetrics
from app.etl.quality.reporter import DataQualityReporter
from app.etl.quality.rules import (
    rule_non_negative_number,
    rule_positive_number,
    rule_required,
    rule_rut,
)
from app.etl.transformation.base import RecordTransformer
from app.etl.validation.base import RecordValidator

# --------------------------------------------------------------------------- #
# Fakes for pipeline integration
# --------------------------------------------------------------------------- #


class FakeSource:
    source_name = "chilecompra_api"

    async def extract(self, run, window: ExtractionWindow | None = None):
        _ = run
        _ = window
        now = datetime.now(timezone.utc)
        return [
            RawRecord(
                source="chilecompra_api",
                resource="contratos",
                source_id="2580-300-LR26",
                payload={
                    "CodigoContrato": "2580-300-LR26",
                    "Estado": "Vigente",
                },
                extracted_at=now,
            )
        ]


class FakeValidator(RecordValidator):
    def validate(self, record: StoredRawRecord) -> ValidationResult:
        if "CodigoContrato" not in record.payload:
            return ValidationResult(is_valid=False)
        return ValidationResult(
            is_valid=True,
            normalized_payload={
                "external_id": record.payload["CodigoContrato"],
                "status": record.payload.get("Estado", "").lower(),
            },
        )


class FakeTransformer(RecordTransformer):
    def transform(self, normalized_payload: dict[str, object]) -> TransformedRecord:
        external_id = str(normalized_payload["external_id"])
        return TransformedRecord(
            entity="contrato",
            natural_key=f"chilecompra:contrato:{external_id}",
            payload={
                "external_id": external_id,
                "status": normalized_payload["status"],
            },
            source_id=external_id,
            payload_hash="hash",
        )


class FakeLoader(RecordLoader):
    def load(self, run, records) -> LoadResult:
        _ = run
        return LoadResult(inserted=len(records))


# --------------------------------------------------------------------------- #
# Reporter unit tests
# --------------------------------------------------------------------------- #


def _run() -> IngestionRunContext:
    return IngestionRunContext(
        ingestion_run_id="ETL-20260806-0001",
        source="chilecompra_api",
        resource="contratos",
        pipeline_version="0.1.0",
        started_at=datetime(2026, 8, 6, 3, 0, 0, tzinfo=timezone.utc),
    )


def test_reporter_emits_and_stores_quality_metrics() -> None:
    reporter = DataQualityReporter()

    # Simulate the pipeline metrics for a run.
    reporter.emit(
        _run(),
        ETLMetrics(valid=90, invalid=10, inserted=80, updated=5, unchanged=3, failed=2),
    )

    assert len(reporter.reports) == 1
    report = reporter.reports[0]
    assert isinstance(report, QualityMetrics)
    assert report.received == 100  # 90 + 10
    assert report.valid == 90
    assert report.invalid == 10
    assert report.errors == 12  # 10 + 2
    assert report.duplicates == 3
    assert report.quality_rate == 0.9


def test_reporter_last_report_property() -> None:
    reporter = DataQualityReporter()
    reporter.emit(_run(), ETLMetrics(valid=1, invalid=0))
    reporter.emit(_run(), ETLMetrics(valid=2, invalid=1))

    assert reporter.last_report is not None
    assert reporter.last_report.valid == 2
    assert reporter.last_report.quality_rate == pytest.approx(2 / 3)


def test_reporter_runs_on_report_callback() -> None:
    seen: list[QualityMetrics] = []

    reporter = DataQualityReporter(on_report=seen.append)
    reporter.emit(_run(), ETLMetrics(valid=5, invalid=0))

    assert len(seen) == 1
    assert seen[0].ingestion_run_id == "ETL-20260806-0001"


def test_reporter_evaluates_payload_rules_per_entity() -> None:
    reporter = DataQualityReporter(
        rules={
            "contrato": [
                lambda p: rule_required(p, "external_id"),
                lambda p: rule_rut(p, "rut"),
            ],
            "adjudicacion": [
                lambda p: rule_positive_number(p, "awarded_amount"),
            ],
        }
    )

    clean = reporter.evaluate_payload_quality(
        "contrato", {"external_id": "2580-300-LR26", "rut": "76123456-7"}
    )
    assert clean.is_clean is True

    bad = reporter.evaluate_payload_quality("adjudicacion", {"awarded_amount": -5})
    assert bad.is_clean is False
    assert bad.violations[0].code == "non_positive_number"

    # No rules configured for an entity -> clean report.
    empty = reporter.evaluate_payload_quality("licitacion", {"external_id": "x"})
    assert empty.is_clean is True


# --------------------------------------------------------------------------- #
# Pipeline integration
# --------------------------------------------------------------------------- #


async def test_pipeline_invokes_quality_reporter_hook() -> None:
    reporter = DataQualityReporter()
    pipeline = ETLPipeline(
        source=FakeSource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=FakeValidator(),
        transformer=FakeTransformer(),
        loader=FakeLoader(),
        quality_reporter=reporter,
    )

    summary = await pipeline.run(run=_run())

    assert summary.metrics.valid == 1
    assert summary.metrics.invalid == 0
    assert len(reporter.reports) == 1
    assert reporter.last_report is not None
    assert reporter.last_report.resource == "contratos"
    assert reporter.last_report.received == 1
    assert reporter.last_report.quality_rate == 1.0


async def test_pipeline_reporter_optional() -> None:
    pipeline = ETLPipeline(
        source=FakeSource(),
        raw_ingestor=InMemoryRawIngestor(),
        validator=FakeValidator(),
        transformer=FakeTransformer(),
        loader=FakeLoader(),
        quality_reporter=None,
    )
    summary = await pipeline.run(run=_run())
    # Without a reporter the pipeline must still complete normally.
    assert summary.metrics.valid == 1
