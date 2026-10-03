from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Protocol

from app.etl.error_handling.models import (
    ErrorType,
    QuarantineRecord,
    issues_to_records,
)
from app.etl.models import StoredRawRecord, ValidationResult

logger = logging.getLogger(__name__)


class Quarantine(Protocol):
    """Receives failed records for durable persistence."""

    def add(self, record: QuarantineRecord) -> None: ...
    def add_many(self, records: list[QuarantineRecord]) -> None: ...
    def all(self) -> list[QuarantineRecord]: ...


class InMemoryQuarantine:
    """Quarantine store backed by a list (tests / architecture validation)."""

    def __init__(self) -> None:
        self._records: list[QuarantineRecord] = []

    def add(self, record: QuarantineRecord) -> None:
        self._records.append(record)

    def add_many(self, records: list[QuarantineRecord]) -> None:
        self._records.extend(records)

    def all(self) -> list[QuarantineRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()

    def by_error_type(self, error_type: str) -> list[QuarantineRecord]:
        return [r for r in self._records if r.error_type == error_type]


class LoggingQuarantine:
    """Quarantine store that emits structured log lines and drops records.

    Useful when no durable backend is configured; the pipeline still reports
    the errors without failing the whole run.
    """

    def add(self, record: QuarantineRecord) -> None:
        logger.warning(
            "quarantine error_type=%s code=%s source=%s resource=%s "
            "source_id=%s run=%s",
            record.error_type,
            record.error_code,
            record.source,
            record.resource,
            record.source_id,
            record.ingestion_run_id,
        )

    def add_many(self, records: list[QuarantineRecord]) -> None:
        for record in records:
            self.add(record)

    def all(self) -> list[QuarantineRecord]:
        return []


class CompoundQuarantine:
    """Fan a record out to multiple quarantine stores (e.g. log + DB)."""

    def __init__(self, stores: list[Quarantine]) -> None:
        self._stores = list(stores)

    def add(self, record: QuarantineRecord) -> None:
        for store in self._stores:
            store.add(record)

    def add_many(self, records: list[QuarantineRecord]) -> None:
        for record in records:
            self.add(record)

    def all(self) -> list[QuarantineRecord]:
        results: list[QuarantineRecord] = []
        for store in self._stores:
            results.extend(store.all())
        return results


# ------------------------------------------------------------------------- #
# Helpers
# ------------------------------------------------------------------------- #
def record_validation_failure(
    quarantine: Quarantine,
    *,
    record: StoredRawRecord,
    result: ValidationResult,
    ingestion_run_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> list[QuarantineRecord]:
    """Persist a failed validation into the quarantine store.

    Returns the records created so callers can inspect/log them.
    """
    if result.is_valid:
        return []

    timestamp = _now()
    options = {
        "source": record.source,
        "resource": record.resource,
        "source_id": record.source_id,
        "payload": record.payload,
        "payload_hash": record.payload_hash,
        "issues": result.issues,
        "timestamp": timestamp,
        "ingestion_run_id": ingestion_run_id or record.ingestion_run_id,
        "metadata": metadata,
    }
    records = issues_to_records(**options)
    if records:
        quarantine.add_many(records)
    return records


def record_processing_error(
    quarantine: Quarantine,
    *,
    error_type: str = ErrorType.UNKNOWN,
    error_code: str = "error",
    message: str = "",
    source: str,
    resource: str,
    source_id: str,
    payload: dict[str, Any],
    payload_hash: str,
    exc: BaseException | None = None,
    retry_count: int = 0,
    max_retries: int | None = 3,
    ingestion_run_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> QuarantineRecord:
    """Record an unexpected processing error into the quarantine store."""
    record = QuarantineRecord(
        error_type=error_type,
        error_code=error_code,
        message=message or str(exc) if exc else message,
        source=source,
        resource=resource,
        source_id=source_id,
        payload=payload,
        payload_hash=payload_hash,
        timestamp=_now(),
        stack_trace=_format_traceback(exc),
        retry_count=retry_count,
        max_retries=max_retries,
        ingestion_run_id=ingestion_run_id,
        metadata=metadata or {},
    )
    quarantine.add(record)
    return record


def _format_traceback(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _now() -> datetime:
    return datetime.now(timezone.utc)
