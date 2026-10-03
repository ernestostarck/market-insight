"""Audit & lineage domain models (Fase 3.13).

Every ETL execution carries an ``ingestion_run_id`` that lets operators answer
the classic audit questions: which source, which resource/endpoint, which
parameters, how many records, how many errors, how long it took and which
pipeline version produced the data.

This module keeps those models as plain dataclasses so they stay decoupled
from any persistence backend (list, structured logs, or an ``audit_runs``
table).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AuditStatus(str, Enum):
    """Outcome of an ETL/audited execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class AuditRecord:
    """Consolidated, human-readable trace of a single ETL execution.

    Attributes
    ----------
    ingestion_run_id
        Unique run identifier, e.g. ``ETL-20260806-00001``.
    source
        Data source, e.g. ``chilecompra_api`` or ``open_data``.
    resource
        Resource stream, e.g. ``licitaciones``.
    endpoint
        Optional endpoint that produced the data (useful for debugging).
    params
        Query parameters / window used by the run.
    pipeline_version
        Version of the pipeline that generated these records.
    started_at
        Wall-clock start of the run.
    finished_at
        Wall-clock end of the run (``None`` while running).
    duration_ms
        Computed elapsed time in milliseconds (``None`` until finished).
    status
        :class:`AuditStatus` of the run.
    """

    ingestion_run_id: str
    source: str
    resource: str
    started_at: datetime
    status: AuditStatus = AuditStatus.SUCCEEDED
    endpoint: str | None = None
    params: dict[str, str] = field(default_factory=dict)
    pipeline_version: str | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    error: str | None = None

    # Record counters (populated from ETL summary metrics).
    extracted: int = 0
    raw_stored: int = 0
    valid: int = 0
    invalid: int = 0
    transformed: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    quarantine: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict (for logs/DB/exports)."""
        return {
            "ingestion_run_id": self.ingestion_run_id,
            "source": self.source,
            "resource": self.resource,
            "endpoint": self.endpoint,
            "params": self.params,
            "pipeline_version": self.pipeline_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "error": self.error,
            "counts": {
                "extracted": self.extracted,
                "raw_stored": self.raw_stored,
                "valid": self.valid,
                "invalid": self.invalid,
                "transformed": self.transformed,
                "inserted": self.inserted,
                "updated": self.updated,
                "unchanged": self.unchanged,
                "failed": self.failed,
                "quarantine": self.quarantine,
            },
            "extra": self.extra,
        }


__all__ = ["AuditStatus", "AuditRecord"]
