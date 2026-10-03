"""Domain models for incremental (delta) ETL loads.

This module captures the state machine that drives incremental syncing:
what triggered a run, which window is being processed, whether the source
has already been backfilled through a given marker, and the outcome of the
most recent run. Keeping these as plain dataclasses decouples the planning
and execution logic from any particular storage backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.etl.models import ETLRunSummary


class IncrementalLoadTrigger(str, Enum):
    """Why an incremental run was scheduled."""

    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"


class IncrementalRunStatus(str, Enum):
    """Lifecycle of an incremental load invocation."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class IncrementalWindow:
    """A contiguous slice of time (or cursor values) to be processed.

    ``start`` is inclusive and ``end`` is inclusive. When both are ``None``
    this represents a full (unbounded) run, e.g. an initial backfill.
    """

    start: datetime | None = None
    end: datetime | None = None

    def is_backfill(self) -> bool:
        return not self.is_incremental()

    def is_incremental(self) -> bool:
        # A window is incremental when it is bounded on both sides.
        return self.start is not None and self.end is not None

    def day_count(self) -> int:
        if self.start is None or self.end is None:
            return 0
        return (self.end.date() - self.start.date()).days + 1

    def split(self, chunk_days: int) -> list["IncrementalWindow"]:
        """Slice the window into sub-windows of at most ``chunk_days`` days.

        Useful for bounding memory usage during a large backfill. Sub-windows
        preserve the same ``is_incremental`` semantics (both bounds).
        """
        if chunk_days < 1:
            raise ValueError("chunk_days must be >= 1")

        start = self.start
        end = self.end
        if start is None or end is None:
            return [self]

        chunks: list[IncrementalWindow] = []
        cursor = start
        step = timedelta(days=chunk_days - 1)
        # Boundaries are inclusive.
        while cursor <= end:
            chunk_end = min(cursor + step, end)
            chunks.append(IncrementalWindow(start=cursor, end=chunk_end))
            cursor = chunk_end + timedelta(days=1)
        return chunks


@dataclass(slots=True)
class IncrementalCheckpoint:
    """Persisted progress marker for a (source, resource) stream.

    ``marker`` is an opaque cursor. For time-based sources it is an ISO date /
    datetime string representing the watermark of data already ingested. For
    offset-based sources (open data) it is a stringified line offset.
    """

    source: str
    resource: str
    marker: str | None
    updated_at: datetime
    last_status: str = "unknown"


@dataclass(slots=True)
class IncrementalPlan:
    """The resolved execution plan for a single sync invocation.

    A plan decides whether to run an incremental delta or a (chunked) backfill
    and, for incremental mode, the concrete window to process based on the last
    checkpoint and the optional explicit lower/upper bounds supplied by the
    caller.
    """

    source: str
    resource: str
    mode: str  # "incremental" | "backfill"
    window: IncrementalWindow | None
    backfill_windows: list[IncrementalWindow] = field(default_factory=list)


@dataclass(slots=True)
class IncrementalRun:
    """Tracks a single incremental load attempt through its lifecycle."""

    source: str
    resource: str
    run_id: str
    window: IncrementalWindow | None
    trigger: IncrementalLoadTrigger = IncrementalLoadTrigger.SCHEDULE
    status: IncrementalRunStatus = IncrementalRunStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    metrics: dict[str, int] = field(default_factory=dict)
    summary: Any | None = None

    def mark_started(self, now: datetime | None = None) -> None:
        self.started_at = now or _utcnow()
        self.status = IncrementalRunStatus.RUNNING

    def mark_succeeded(
        self,
        summary: ETLRunSummary | None = None,
        now: datetime | None = None,
    ) -> None:
        self.finished_at = now or _utcnow()
        self.status = IncrementalRunStatus.SUCCEEDED
        self.summary = summary
        # Preserve metrics already accumulated by the engine (e.g. summed
        # across backfill chunks). Only derive them from the summary when the
        # caller has not accumulated anything yet.
        if not self.metrics:
            self.metrics = _metrics_from_summary(summary)

    def mark_failed(
        self,
        error: str,
        now: datetime | None = None,
    ) -> None:
        self.finished_at = now or _utcnow()
        self.status = IncrementalRunStatus.FAILED
        self.error = error


def _metrics_from_summary(summary: ETLRunSummary | None) -> dict[str, int]:
    if summary is None:
        return {}
    m = summary.metrics
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


def _utcnow() -> datetime:
    from datetime import timezone

    return datetime.now(timezone.utc)
