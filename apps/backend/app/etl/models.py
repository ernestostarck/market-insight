from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class IngestionRunContext:
    ingestion_run_id: str
    source: str
    resource: str
    pipeline_version: str
    started_at: datetime
    params: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RawRecord:
    source: str
    resource: str
    source_id: str
    payload: dict[str, Any]
    extracted_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class StoredRawRecord:
    source: str
    resource: str
    source_id: str
    payload: dict[str, Any]
    payload_hash: str
    received_at: datetime
    ingestion_run_id: str


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    normalized_payload: dict[str, Any] | None = None
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass(slots=True)
class TransformedRecord:
    entity: str
    natural_key: str
    payload: dict[str, Any]
    source_id: str
    payload_hash: str


@dataclass(slots=True)
class LoadResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0


@dataclass(slots=True)
class ETLMetrics:
    extracted: int = 0
    raw_stored: int = 0
    valid: int = 0
    invalid: int = 0
    transformed: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0


@dataclass(slots=True)
class ETLRunSummary:
    run: IngestionRunContext
    metrics: ETLMetrics
    quarantine_count: int
