"""Audit record builders / lineage helpers (Fase 3.13).

These functions turn the coarse run context + summary metrics (and the
incremental run lifecycle) into a rich :class:`AuditRecord` that answers the
lineage questions: what was synced, when, with which parameters, how many
records flowed through each stage, how long it took and whether it succeeded.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.etl.audit.models import AuditRecord, AuditStatus
from app.etl.models import ETLMetrics, ETLRunSummary, IngestionRunContext


def build_audit_record(
    run: IngestionRunContext,
    summary: ETLRunSummary | None = None,
    *,
    endpoint: str | None = None,
    status: AuditStatus = AuditStatus.SUCCEEDED,
    error: str | None = None,
    finished_at: datetime | None = None,
    extra: dict[str, Any] | None = None,
) -> AuditRecord:
    """Build an :class:`AuditRecord` from run context and optional summary.

    ``duration_ms`` is derived from ``started_at``/``finished_at`` when both
    are available.
    """
    finish = finished_at or datetime.now(timezone.utc)
    duration_ms = _duration_ms(run.started_at, finish)

    metrics = summary.metrics if summary is not None else None
    return AuditRecord(
        ingestion_run_id=run.ingestion_run_id,
        source=run.source,
        resource=run.resource,
        started_at=run.started_at,
        status=status,
        endpoint=endpoint,
        params=dict(run.params),
        pipeline_version=run.pipeline_version,
        finished_at=finish,
        duration_ms=duration_ms,
        error=error,
        extracted=_metric(metrics, "extracted"),
        raw_stored=_metric(metrics, "raw_stored"),
        valid=_metric(metrics, "valid"),
        invalid=_metric(metrics, "invalid"),
        transformed=_metric(metrics, "transformed"),
        inserted=_metric(metrics, "inserted"),
        updated=_metric(metrics, "updated"),
        unchanged=_metric(metrics, "unchanged"),
        failed=_metric(metrics, "failed"),
        quarantine=summary.quarantine_count if summary is not None else 0,
        extra=extra or {},
    )


def audit_from_incremental(
    run: Any,
    summary: ETLRunSummary | None = None,
    *,
    endpoint: str | None = None,
) -> AuditRecord:
    """Build an :class:`AuditRecord` from an incremental :class:`IncrementalRun`.

    Accepts the incremental run object (which carries ``run_id``, ``source``,
    ``resource``, ``started_at``, ``finished_at``, ``status``, ``error`` and
    ``metrics``) and derives the audit fields from it. This is used by the
    :class:`~app.etl.incremental.engine.IncrementalETL` integration so the
    audit reporter sees a single consolidated record per execution.
    """
    metrics = run.metrics or _metrics_dict(summary)
    succeeded = getattr(run, "status", None)
    status = (
        AuditStatus.SUCCEEDED
        if succeeded is None or _is_success(succeeded)
        else AuditStatus.FAILED
    )
    error = getattr(run, "error", None)
    started_at = getattr(run, "started_at", None) or datetime.now(timezone.utc)
    finished_at = getattr(run, "finished_at", None)

    return AuditRecord(
        ingestion_run_id=getattr(run, "run_id", None) or "unknown",
        source=getattr(run, "source", None) or "unknown",
        resource=getattr(run, "resource", None) or "unknown",
        started_at=started_at,
        status=status,
        endpoint=endpoint,
        params=dict(getattr(run, "params", {}) or {}),
        pipeline_version=_incremental_pipeline_version(),
        finished_at=finished_at,
        duration_ms=_duration_ms(started_at, finished_at),
        error=error,
        extracted=int(metrics.get("extracted", 0)),
        raw_stored=int(metrics.get("raw_stored", 0)),
        valid=int(metrics.get("valid", 0)),
        invalid=int(metrics.get("invalid", 0)),
        transformed=int(metrics.get("transformed", 0)),
        inserted=int(metrics.get("inserted", 0)),
        updated=int(metrics.get("updated", 0)),
        unchanged=int(metrics.get("unchanged", 0)),
        failed=int(metrics.get("failed", 0)),
        quarantine=int(metrics.get("quarantine", 0)),
    )


def _is_success(status: Any) -> bool:
    value = getattr(status, "value", status)
    return str(value).lower() in {"succeeded", "success", "ok"}


def _metrics_dict(summary: ETLRunSummary | None) -> dict[str, int]:
    if summary is None:
        return {}
    m: ETLMetrics = summary.metrics
    return {
        "extracted": m.extracted,
        "raw_stored": m.raw_stored,
        "valid": m.valid,
        "invalid": m.invalid,
        "transformed": m.transformed,
        "inserted": m.inserted,
        "updated": m.updated,
        "unchanged": m.unchanged,
        "failed": m.failed,
        "quarantine": summary.quarantine_count,
    }


def _metric(metrics: ETLMetrics | None, key: str) -> int:
    if metrics is None:
        return 0
    return int(getattr(metrics, key, 0))


def _duration_ms(
    started_at: datetime | None,
    finished_at: datetime | None,
) -> float | None:
    if started_at is None or finished_at is None:
        return None
    return round((finished_at - started_at).total_seconds() * 1000, 3)


def _incremental_pipeline_version() -> str:
    # Kept in sync with the engine's _PIPELINE_VERSION.
    return "0.1.0"


__all__ = ["build_audit_record", "audit_from_incremental"]
