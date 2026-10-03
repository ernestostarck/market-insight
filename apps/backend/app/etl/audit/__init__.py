"""Audit & lineage layer for the ETL pipeline (Fase 3.13).

Every ETL execution is identified by an ``ingestion_run_id`` and a
consolidated :class:`AuditRecord` captures the lineage: source, resource,
endpoint, parameters, pipeline version, timings, and per-stage record counts.
The records are handed to an :class:`AuditReporter` for durable persistence
(logs, database, etc.) without coupling the engine to a concrete backend.
"""

from __future__ import annotations

from app.etl.audit.lineage import audit_from_incremental, build_audit_record
from app.etl.audit.models import AuditRecord, AuditStatus
from app.etl.audit.reporter import (
    AuditReporter,
    CompoundAuditReporter,
    InMemoryAuditReporter,
    LoggingAuditReporter,
)

__all__ = [
    "AuditRecord",
    "AuditStatus",
    "AuditReporter",
    "InMemoryAuditReporter",
    "LoggingAuditReporter",
    "CompoundAuditReporter",
    "build_audit_record",
    "audit_from_incremental",
]
