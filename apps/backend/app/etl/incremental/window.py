"""Window planning for incremental and backfill ETL loads.

The central idea is that a ``(source, resource)`` stream keeps a progress
watermark (a checkpoint). On every scheduled run we must decide:

* If no watermark exists yet, this is a backfill: process the whole history,
  optionally chunked to bound memory and to allow resumability at day
  boundaries.
* If a watermark exists, this is an incremental run: process only the data
  between the watermark and the requested upper bound (usually "now"), then
  advance the watermark.

This module only *plans* the windows; execution is left to the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from app.etl.incremental.models import IncrementalPlan, IncrementalWindow


class _CheckpointLike(Protocol):
    marker: str | None


@dataclass(slots=True)
class IncrementalPlanner:
    """Plans incremental / backfill windows from checkpoint state."""

    #: Number of days per chunk when performing a (resumable) backfill.
    backfill_chunk_days: int = 30
    #: Distribution of the backfill windows (left-open on purpose so chunks
    #: never overlap); inclusive both ends on the first chunk only.
    include_boundary_overlap: bool = False

    def build_plan(
        self,
        *,
        source: str,
        resource: str,
        checkpoint: _CheckpointLike | None,
        history_start: date | None = None,
        end_at: datetime | None = None,
        force_backfill: bool = False,
    ) -> IncrementalPlan:
        """Build the execution plan for a stream.

        Parameters
        ----------
        source
            Source identifier (e.g. ``chilecompra_api``).
        resource
            Resource identifier within the source (e.g. ``licitaciones``).
        checkpoint
            Current checkpoint (``None`` means never synced -> backfill). The
            concrete type is duck-typed; we only read ``marker``.
        history_start
            Earliest date to consider when backfilling. Required (or a default
            is used) when no checkpoint exists.
        end_at
            Upper bound for the run. Defaults to now (UTC).
        force_backfill
            Ignore the checkpoint and force a full backfill.
        """
        now = end_at if end_at is not None else _utcnow()

        if force_backfill or checkpoint is None:
            return self._backfill_plan(
                source=source,
                resource=resource,
                history_start=history_start,
                now=now,
            )

        watermark = checkpoint.marker
        if watermark is None:
            return self._backfill_plan(
                source=source,
                resource=resource,
                history_start=history_start,
                now=now,
            )

        cursor = _parse_watermark(watermark)
        if cursor is None:
            # Unparseable watermark: fall back to a full backfill from the
            # requested history (safe default; avoids silently skipping data).
            return self._backfill_plan(
                source=source,
                resource=resource,
                history_start=history_start,
                now=now,
            )

        return IncrementalPlan(
            source=source,
            resource=resource,
            mode="incremental",
            window=IncrementalWindow(start=cursor, end=now),
            backfill_windows=[],
        )

    def _backfill_plan(
        self,
        *,
        source: str,
        resource: str,
        history_start: date | None,
        now: datetime,
    ) -> IncrementalPlan:
        start = history_start if history_start is not None else _default_history_start()
        start_dt = _as_datetime(start)
        if start_dt > now:
            raise ValueError("history_start must not be after end_at")

        full = IncrementalWindow(start=start_dt, end=now)
        chunks = full.split(self.backfill_chunk_days)
        return IncrementalPlan(
            source=source,
            resource=resource,
            mode="backfill",
            window=None,
            backfill_windows=chunks,
        )


def _parse_watermark(marker: str) -> datetime | None:
    """Parse a watermark marker into an aware datetime.

    Accepts ``YYYY-MM-DD`` (midnight UTC) and ISO ``YYYY-MM-DDTHH:MM:SS``.
    Returns ``None`` when the value cannot be interpreted as a time marker
    (e.g. offset-based streams), which callers treat as "needs backfill".
    """
    candidate = marker.strip()
    if not candidate:
        return None

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(candidate, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _as_datetime(value: date) -> datetime:
    if isinstance(value, datetime):
        dt = value
        return dt.replace(tzinfo=dt.tzinfo or timezone.utc)
    return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)


def _default_history_start() -> date:
    # Reasonable default horizon for the market data domain (5 years back).
    return date.today() - timedelta(days=5 * 365)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
