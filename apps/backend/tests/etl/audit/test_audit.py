from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.etl.audit.lineage import audit_from_incremental, build_audit_record
from app.etl.audit.models import AuditRecord, AuditStatus
from app.etl.audit.reporter import (
    CompoundAuditReporter,
    InMemoryAuditReporter,
    LoggingAuditReporter,
)
from app.etl.incremental.models import (
    IncrementalLoadTrigger,
    IncrementalRun,
    IncrementalRunStatus,
)
from app.etl.models import ETLMetrics, ETLRunSummary, IngestionRunContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _run_context(
    ingestion_run_id: str = "ETL-20260806-00001",
    *,
    source: str = "chilecompra_api",
    resource: str = "licitaciones",
    pipeline_version: str = "3.13.0",
) -> IngestionRunContext:
    return IngestionRunContext(
        ingestion_run_id=ingestion_run_id,
        source=source,
        resource=resource,
        pipeline_version=pipeline_version,
        started_at=_now(),
        params={"mode": "incremental", "window_start": "2026-08-05"},
    )


def _summary(
    run: IngestionRunContext,
    *,
    metrics: ETLMetrics | None = None,
) -> ETLRunSummary:
    return ETLRunSummary(
        run=run,
        metrics=metrics or ETLMetrics(extracted=10, valid=9, invalid=1, inserted=9),
        quarantine_count=1,
    )


# --------------------------------------------------------------------- #
# AuditRecord / models
# --------------------------------------------------------------------- #
def test_audit_record_to_dict_serializes_all_fields() -> None:
    started = _now()
    finished = started + timedelta(seconds=2)
    record = AuditRecord(
        ingestion_run_id="ETL-20260806-00001",
        source="chilecompra_api",
        resource="licitaciones",
        started_at=started,
        finished_at=finished,
        duration_ms=2000.0,
        status=AuditStatus.SUCCEEDED,
        endpoint="/licitaciones.json",
        params={"mode": "incremental"},
        pipeline_version="3.13.0",
        extracted=10,
        valid=9,
        invalid=1,
        inserted=9,
        quarantine=1,
    )

    data = record.to_dict()

    assert data["ingestion_run_id"] == "ETL-20260806-00001"
    assert data["status"] == "succeeded"
    assert data["endpoint"] == "/licitaciones.json"
    assert data["duration_ms"] == 2000.0
    assert data["counts"]["inserted"] == 9
    assert "started_at" in data
    assert "finished_at" in data


def test_audit_record_defaults() -> None:
    record = AuditRecord(
        ingestion_run_id="RUN-1",
        source="s",
        resource="r",
        started_at=_now(),
    )
    assert record.status == AuditStatus.SUCCEEDED
    assert record.duration_ms is None
    assert record.endpoint is None
    assert record.pipeline_version is None
    assert record.error is None
    assert record.finished_at is None


# --------------------------------------------------------------------- #
# build_audit_record
# --------------------------------------------------------------------- #
def test_build_audit_record_from_run_and_summary() -> None:
    run = _run_context()
    summary = _summary(run)

    audit = build_audit_record(run, summary, endpoint="/licitaciones.json")

    assert audit.ingestion_run_id == run.ingestion_run_id
    assert audit.source == run.source
    assert audit.resource == run.resource
    assert audit.pipeline_version == run.pipeline_version
    assert audit.endpoint == "/licitaciones.json"
    assert audit.params == run.params
    assert audit.extracted == 10
    assert audit.valid == 9
    assert audit.invalid == 1
    assert audit.inserted == 9
    assert audit.quarantine == 1
    assert audit.status == AuditStatus.SUCCEEDED
    assert audit.duration_ms is not None


def test_build_audit_record_failed_run_carries_error() -> None:
    run = _run_context()
    finish = _now()

    audit = build_audit_record(
        run,
        None,
        status=AuditStatus.FAILED,
        error="boom",
        finished_at=finish,
    )

    assert audit.status == AuditStatus.FAILED
    assert audit.error == "boom"
    assert audit.finished_at == finish
    assert audit.duration_ms is not None
    # No summary -> counters are zero.
    assert audit.valid == 0
    assert audit.quarantine == 0


# --------------------------------------------------------------------- #
# audit_from_incremental
# --------------------------------------------------------------------- #
def test_audit_from_incremental_success() -> None:
    started = _now()
    finished = started + timedelta(seconds=3)
    run = IncrementalRun(
        source="chilecompra_api",
        resource="licitaciones",
        run_id="ETL-20260806-00001",
        window=None,
        trigger=IncrementalLoadTrigger.SCHEDULE,
        status=IncrementalRunStatus.SUCCEEDED,
        started_at=started,
        finished_at=finished,
        metrics={"extracted": 10, "valid": 9, "invalid": 1, "inserted": 9},
    )

    audit = audit_from_incremental(run, endpoint="/licitaciones.json")

    assert audit.ingestion_run_id == "ETL-20260806-00001"
    assert audit.source == "chilecompra_api"
    assert audit.resource == "licitaciones"
    assert audit.status == AuditStatus.SUCCEEDED
    assert audit.extracted == 10
    assert audit.valid == 9
    assert audit.invalid == 1
    assert audit.inserted == 9
    assert audit.duration_ms == 3000.0


def test_audit_from_incremental_failure() -> None:
    started = _now()
    run = IncrementalRun(
        source="chilecompra_api",
        resource="ordenes_compra",
        run_id="ETL-20260806-00002",
        window=None,
        trigger=IncrementalLoadTrigger.SCHEDULE,
        status=IncrementalRunStatus.FAILED,
        started_at=started,
        finished_at=None,
        error="connection refused",
        metrics={},
    )

    audit = audit_from_incremental(run)

    assert audit.status == AuditStatus.FAILED
    assert audit.error == "connection refused"
    assert audit.finished_at is None
    assert audit.duration_ms is None


# --------------------------------------------------------------------- #
# Reporters
# --------------------------------------------------------------------- #
def test_in_memory_audit_reporter_accumulates() -> None:
    reporter = InMemoryAuditReporter()
    run = _run_context(ingestion_run_id="RUN-A")
    reporter.emit(build_audit_record(run, _summary(run)))
    reporter.emit(
        build_audit_record(
            _run_context(ingestion_run_id="RUN-B"),
            _summary(_run_context(ingestion_run_id="RUN-B")),
        )
    )

    assert reporter.count() == 2
    assert reporter.last is not None
    assert reporter.last.ingestion_run_id == "RUN-B"
    assert len(reporter.by_run("RUN-A")) == 1


def test_compound_audit_reporter_fans_out() -> None:
    in_memory = InMemoryAuditReporter()
    logging_reporter = LoggingAuditReporter()
    compound = CompoundAuditReporter([in_memory, logging_reporter])

    run = _run_context()
    compound.emit(build_audit_record(run, _summary(run)))

    assert in_memory.count() == 1
