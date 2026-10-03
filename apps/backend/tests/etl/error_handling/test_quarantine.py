from __future__ import annotations

from datetime import datetime, timezone

import pytest
from app.etl.error_handling.models import (
    ErrorType,
    QuarantineRecord,
    issues_to_records,
)
from app.etl.error_handling.quarantine import (
    CompoundQuarantine,
    InMemoryQuarantine,
    LoggingQuarantine,
    record_processing_error,
    record_validation_failure,
)
from app.etl.models import (
    StoredRawRecord,
    ValidationIssue,
    ValidationResult,
)


def _raw_record(
    *,
    resource: str = "licitaciones",
    source_id: str = "1000-1-LR26",
    payload: dict | None = None,
    run_id: str = "ETL-run-1",
) -> StoredRawRecord:
    return StoredRawRecord(
        source="chilecompra_api",
        resource=resource,
        source_id=source_id,
        payload=payload or {"CodigoExterno": source_id, "Estado": "PUBLICADA"},
        payload_hash="abc123",
        received_at=datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc),
        ingestion_run_id=run_id,
    )


def test_quarantine_record_can_retry() -> None:
    record = QuarantineRecord(
        error_type=ErrorType.VALIDATION,
        source="chilecompra_api",
        resource="licitaciones",
        source_id="1000-1-LR26",
        payload={},
        payload_hash="h",
        timestamp=datetime.now(timezone.utc),
        retry_count=0,
        max_retries=3,
    )
    assert record.can_retry() is True

    record.retry_count = 3
    assert record.can_retry() is False

    record.retry_count = 5
    record.max_retries = None
    assert record.can_retry() is True


def test_in_memory_quarantine_stores_and_filters() -> None:
    store = InMemoryQuarantine()
    store.add(
        QuarantineRecord(
            error_type=ErrorType.VALIDATION,
            source="chilecompra_api",
            resource="licitaciones",
            source_id="1",
            payload={},
            payload_hash="h1",
            timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
            error_code="invalid_date",
        )
    )
    store.add(
        QuarantineRecord(
            error_type=ErrorType.TRANSFORMATION,
            source="chilecompra_api",
            resource="contratos",
            source_id="2",
            payload={},
            payload_hash="h2",
            timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
            error_code="boom",
        )
    )

    assert store.count() == 2
    assert len(store.by_error_type(ErrorType.VALIDATION)) == 1
    assert len(store.by_error_type(ErrorType.TRANSFORMATION)) == 1
    assert len(store.all()) == 2


def test_record_validation_failure_persists_each_issue() -> None:
    store = InMemoryQuarantine()
    raw = _raw_record()
    result = ValidationResult(
        is_valid=False,
        issues=[
            ValidationIssue(code="invalid_date", message="Bad date", field="Fecha"),
            ValidationIssue(code="missing_field", message="Missing", field="Estado"),
        ],
    )

    created = record_validation_failure(
        store,
        record=raw,
        result=result,
        ingestion_run_id="ETL-run-1",
    )

    assert len(created) == 2
    assert store.count() == 2
    first = created[0]
    assert first.error_type == ErrorType.VALIDATION
    assert first.error_code == "invalid_date"
    assert first.source_id == "1000-1-LR26"
    assert first.ingestion_run_id == "ETL-run-1"
    assert first.payload == raw.payload
    assert first.payload_hash == raw.payload_hash


def test_record_validation_failure_returns_empty_when_valid() -> None:
    store = InMemoryQuarantine()
    raw = _raw_record()
    result = ValidationResult(is_valid=True, normalized_payload={"external_id": "x"})

    created = record_validation_failure(store, record=raw, result=result)

    assert created == []
    assert store.count() == 0


def test_record_processing_error_captures_stack_trace() -> None:
    store = InMemoryQuarantine()

    captured: list[BaseException] = []

    def _boom() -> None:
        raise ValueError("exploded")

    try:
        _boom()
    except ValueError as exc:
        captured.append(exc)

    assert len(captured) == 1
    exc = captured[0]
    record = record_processing_error(
        store,
        error_type=ErrorType.TRANSFORMATION,
        error_code=type(exc).__name__,
        message=str(exc),
        source="chilecompra_api",
        resource="contratos",
        source_id="2580-300-LR26",
        payload={"Codigo": "2580-300-LR26"},
        payload_hash="xyz",
        exc=exc,
        ingestion_run_id="ETL-run-2",
    )

    assert store.count() == 1
    assert record.error_type == ErrorType.TRANSFORMATION
    assert record.error_code == "ValueError"
    assert record.message == "exploded"
    assert record.stack_trace is not None
    assert "_boom" in record.stack_trace


def test_compound_quarantine_fans_out() -> None:
    memory = InMemoryQuarantine()
    logging_store = LoggingQuarantine()
    compound = CompoundQuarantine([memory, logging_store])

    record = QuarantineRecord(
        error_type=ErrorType.VALIDATION,
        source="chilecompra_api",
        resource="licitaciones",
        source_id="1",
        payload={},
        payload_hash="h",
        timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )
    compound.add(record)

    assert memory.count() == 1
    assert compound.all() == [record]


def test_issues_to_records_builds_quarantine_records() -> None:
    records = issues_to_records(
        source="chilecompra_api",
        resource="licitaciones",
        source_id="1000-1-LR26",
        payload={"a": 1},
        payload_hash="h",
        issues=[ValidationIssue(code="invalid_date", message="Bad", field="Fecha")],
        timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
        ingestion_run_id="ETL-run-3",
    )

    assert len(records) == 1
    assert records[0].error_code == "invalid_date"
    assert records[0].field == "Fecha"
    assert records[0].ingestion_run_id == "ETL-run-3"


def test_logging_quarantine_is_noop_for_all() -> None:
    store = LoggingQuarantine()
    record = QuarantineRecord(
        error_type=ErrorType.UNKNOWN,
        source="s",
        resource="r",
        source_id="id",
        payload={},
        payload_hash="h",
        timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )
    store.add(record)
    store.add_many([record])
    assert store.all() == []


def test_in_memory_quarantine_clear() -> None:
    store = InMemoryQuarantine()
    store.add(
        QuarantineRecord(
            error_type=ErrorType.UNKNOWN,
            source="s",
            resource="r",
            source_id="id",
            payload={},
            payload_hash="h",
            timestamp=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )
    )
    assert store.count() == 1
    store.clear()
    assert store.count() == 0
