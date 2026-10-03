from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime
from typing import Any

from app.etl.models import ValidationIssue


class ErrorType:
    """Well-known error categories recorded in quarantine."""

    VALIDATION = "validation"
    NORMALIZATION = "normalization"
    TRANSFORMATION = "transformation"
    LOADING = "loading"
    EXTRACTION = "extraction"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class QuarantineRecord:
    """A single failed/errored record preserved for analysis and retries.

    Attributes
    ----------
    error_type
        Category of the error (one of :class:`ErrorType`).
    source
        Data source the record came from (e.g. ``chilecompra_api``).
    resource
        ETL resource name (e.g. ``licitaciones``).
    source_id
        Natural identifier of the original record.
    payload
        Original (raw) payload. Kept intact so nothing is lost.
    payload_hash
        Hash of the original payload for cross-referencing.
    timestamp
        When the error was recorded.
    error_code
        Stable machine-readable error code (e.g. ``invalid_date``).
    message
        Human-readable description of the failure.
    field
        Payload field that triggered the error, when applicable.
    stack_trace
        Formatted stack trace for unexpected processing errors.
    retry_count
        Number of times this record has been retried.
    max_retries
        Upper bound on automatic retries (``None`` = unlimited).
    ingestion_run_id
        Identifies the ETL run that produced this error.
    metadata
        Extra context (endpoint, page, snapshot date, ...).
    """

    error_type: str
    source: str
    resource: str
    source_id: str
    payload: dict[str, Any]
    payload_hash: str
    timestamp: datetime
    error_code: str = "error"
    message: str = ""
    field: str | None = None
    stack_trace: str | None = None
    retry_count: int = 0
    max_retries: int | None = 3
    ingestion_run_id: str | None = None
    metadata: dict[str, str] = dc_field(default_factory=dict)

    def can_retry(self) -> bool:
        """Whether the record is eligible for another automatic retry."""
        if self.max_retries is None:
            return True
        return self.retry_count < self.max_retries


@dataclass(slots=True)
class ValidationFailure:
    """A validation failure extracted from a :class:`ValidationResult`."""

    issue: ValidationIssue
    is_fatal: bool = True

    def to_record(
        self,
        *,
        source: str,
        resource: str,
        source_id: str,
        payload: dict[str, Any],
        payload_hash: str,
        timestamp: datetime,
        ingestion_run_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> QuarantineRecord:
        """Build a quarantine record from this validation issue."""
        return QuarantineRecord(
            error_type=ErrorType.VALIDATION,
            source=source,
            resource=resource,
            source_id=source_id,
            payload=payload,
            payload_hash=payload_hash,
            timestamp=timestamp,
            error_code=self.issue.code,
            message=self.issue.message,
            field=self.issue.field,
            ingestion_run_id=ingestion_run_id,
            metadata=metadata or {},
        )


def issues_to_records(
    *,
    source: str,
    resource: str,
    source_id: str,
    payload: dict[str, Any],
    payload_hash: str,
    issues: list[ValidationIssue],
    timestamp: datetime,
    ingestion_run_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> list[QuarantineRecord]:
    """Convert a list of validation issues into quarantine records."""
    return [
        ValidationFailure(issue=issue).to_record(
            source=source,
            resource=resource,
            source_id=source_id,
            payload=payload,
            payload_hash=payload_hash,
            timestamp=timestamp,
            ingestion_run_id=ingestion_run_id,
            metadata=metadata,
        )
        for issue in issues
    ]
