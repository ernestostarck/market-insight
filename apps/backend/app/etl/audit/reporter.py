"""Audit reporters for the ETL pipeline (Fase 3.13).

An :class:`AuditReporter` receives a completed :class:`AuditRecord` after each
run so the audit trail can be persisted (database, structured logs, dead-letter
queue) without coupling the engine to a concrete backend. This mirrors the
Protocol-based pattern used elsewhere (:class:`QualityReporter`, :class:`Quarantine`).
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.etl.audit.models import AuditRecord

logger = logging.getLogger(__name__)


class AuditReporter(Protocol):
    """Receives a completed :class:`AuditRecord` for durable persistence."""

    def emit(self, audit: AuditRecord) -> None: ...


class InMemoryAuditReporter:
    """Audit reporter that accumulates records in a list (tests/architecture)."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def emit(self, audit: AuditRecord) -> None:
        self.records.append(audit)

    @property
    def last(self) -> AuditRecord | None:
        return self.records[-1] if self.records else None

    def count(self) -> int:
        return len(self.records)

    def clear(self) -> None:
        self.records.clear()

    def by_run(self, ingestion_run_id: str) -> list[AuditRecord]:
        return [r for r in self.records if r.ingestion_run_id == ingestion_run_id]


class LoggingAuditReporter:
    """Audit reporter that emits structured log lines (observability)."""

    def emit(self, audit: AuditRecord) -> None:
        logger.info(
            "audit run=%s source=%s resource=%s status=%s endpoint=%s "
            "duration_ms=%s extracted=%d valid=%d invalid=%d inserted=%d "
            "updated=%d unchanged=%d failed=%d quarantine=%d version=%s",
            audit.ingestion_run_id,
            audit.source,
            audit.resource,
            audit.status.value,
            audit.endpoint,
            audit.duration_ms,
            audit.extracted,
            audit.valid,
            audit.invalid,
            audit.inserted,
            audit.updated,
            audit.unchanged,
            audit.failed,
            audit.quarantine,
            audit.pipeline_version,
        )
        if audit.error:
            logger.error(
                "audit error run=%s resource=%s error=%s",
                audit.ingestion_run_id,
                audit.resource,
                audit.error,
            )


class CompoundAuditReporter:
    """Fan an audit record out to multiple reporters (e.g. log + DB)."""

    def __init__(self, reporters: list[AuditReporter]) -> None:
        self._reporters = list(reporters)

    def emit(self, audit: AuditRecord) -> None:
        for reporter in self._reporters:
            reporter.emit(audit)


__all__ = [
    "AuditReporter",
    "InMemoryAuditReporter",
    "LoggingAuditReporter",
    "CompoundAuditReporter",
]
