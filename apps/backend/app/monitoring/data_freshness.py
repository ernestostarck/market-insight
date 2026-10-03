"""Data Freshness evaluation service for ChileCompra ingestion pipelines.

Calculates data freshness delta (seconds) between the latest processed tender
and the current UTC timestamp. Evaluates operational states (NORMAL, WARNING, CRITICAL)
derived from the real publication and synchronization cycles of Mercado Publico / ChileCompra:
- NORMAL: <= 18 hours (typical daily business day synchronization cycle, 08:00 to 19:00 CLT).
- WARNING: > 18 hours and <= 36 hours (tolerates weekend transitions and minor ingestion delays).
- CRITICAL: > 36 hours (indicates prolonged failure, broken token, or upstream API downtime).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.monitoring.metrics import (
    DATA_FRESHNESS_SECONDS,
    ETL_LAST_SUCCESS_TIMESTAMP,
)

logger = logging.getLogger(__name__)

#: ETL resource whose last successful run defines "how fresh is the data" (tenders).
#: It is the ``pipeline`` label the ETL jobs record, i.e. the resource name.
PRIMARY_PIPELINE = "licitaciones"

# Calibrated operational thresholds based on ChileCompra publication frequency
FRESHNESS_NORMAL_MAX_SECONDS: float = 18.0 * 3600.0  # 64,800 s (18 hours)
FRESHNESS_WARNING_MAX_SECONDS: float = 36.0 * 3600.0  # 129,600 s (36 hours)


class FreshnessState(str, Enum):
    """Operational state of dataset freshness."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class DataFreshnessReport(BaseModel):
    """Detailed report of data freshness evaluation."""

    status: FreshnessState = Field(
        ...,
        description="Freshness state based on ChileCompra operational thresholds (normal, warning, critical).",
    )
    freshness_seconds: float | None = Field(
        None,
        description="Time delta in seconds between latest processed record and current UTC time.",
    )
    last_processed_timestamp: str | None = Field(
        None,
        description="ISO-8601 string of the latest processed tender timestamp.",
    )
    source: str = Field(
        default="unknown",
        description="Source of the evaluated timestamp (database, etl_metrics, fallback).",
    )
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "normal_max_seconds": FRESHNESS_NORMAL_MAX_SECONDS,
            "warning_max_seconds": FRESHNESS_WARNING_MAX_SECONDS,
        },
        description="Active threshold boundaries in seconds.",
    )
    message: str = Field(
        default="",
        description="Operational summary message describing freshness status.",
    )


def get_latest_processed_timestamp(db: Any = None) -> tuple[datetime | None, str]:
    """Retrieve the latest processed record timestamp.

    Queries the database tenders table when available, falling back to
    the Prometheus ETL last success timestamp metric.
    """
    # 1. Attempt database query
    if db is not None:
        try:
            from app.models.core import Licitacion  # type: ignore[attr-defined]

            # Query the maximum updated_at
            stmt = select(func.max(Licitacion.updated_at))
            db_max = db.scalar(stmt)
            if db_max is not None and isinstance(db_max, datetime):
                if db_max.tzinfo is None:
                    db_max = db_max.replace(tzinfo=UTC)
                return db_max, "database"
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not extract latest timestamp from database: %s", exc)

    # 2. Fallback to in-memory / Prometheus gauge ETL_LAST_SUCCESS_TIMESTAMP
    try:
        metric_samples = getattr(ETL_LAST_SUCCESS_TIMESTAMP, "_samples", None)
        if callable(metric_samples):
            for sample in metric_samples():
                if sample.labels.get("pipeline") == PRIMARY_PIPELINE and sample.value > 0:
                    return datetime.fromtimestamp(sample.value, tz=UTC), "etl_metrics"
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not extract timestamp from ETL_LAST_SUCCESS_TIMESTAMP metric: %s", exc)

    return None, "none"


def classify_freshness_state(freshness_seconds: float | None) -> tuple[FreshnessState, str]:
    """Classify the freshness seconds against ChileCompra operational thresholds."""
    if freshness_seconds is None:
        return (
            FreshnessState.NORMAL,
            "No historical ingestion records available; fresh state assumed.",
        )

    if freshness_seconds <= FRESHNESS_NORMAL_MAX_SECONDS:
        hours = round(freshness_seconds / 3600.0, 1)
        return (
            FreshnessState.NORMAL,
            f"Data is up-to-date ({hours}h old <= 18h threshold).",
        )

    if freshness_seconds <= FRESHNESS_WARNING_MAX_SECONDS:
        hours = round(freshness_seconds / 3600.0, 1)
        return (
            FreshnessState.WARNING,
            f"Data freshness degraded ({hours}h old > 18h, <= 36h). Possible delayed batch or weekend interval.",
        )

    hours = round(freshness_seconds / 3600.0, 1)
    return (
        FreshnessState.CRITICAL,
        f"Data freshness critical ({hours}h old > 36h threshold). Immediate pipeline triage required.",
    )


def _build_report(latest_dt: datetime | None, source: str) -> DataFreshnessReport:
    """Classify a latest-processed timestamp, record the Prometheus gauge, return the report."""
    now_utc = datetime.now(UTC)

    freshness_seconds: float | None = None
    last_processed_iso: str | None = None

    if latest_dt is not None:
        last_processed_iso = latest_dt.isoformat()
        diff = (now_utc - latest_dt).total_seconds()
        freshness_seconds = round(max(0.0, diff), 1)

    state, msg = classify_freshness_state(freshness_seconds)

    # Expose current freshness seconds to Prometheus gauge
    if freshness_seconds is not None:
        DATA_FRESHNESS_SECONDS.set(freshness_seconds)

    return DataFreshnessReport(
        status=state,
        freshness_seconds=freshness_seconds,
        last_processed_timestamp=last_processed_iso,
        source=source,
        message=msg,
    )


def evaluate_data_freshness(
    db: Any = None,
    pipeline: str = PRIMARY_PIPELINE,
) -> DataFreshnessReport:
    """Evaluate current data freshness, record Prometheus gauge, and return report."""
    latest_dt, source = get_latest_processed_timestamp(db)
    return _build_report(latest_dt, source)


async def get_last_successful_run_timestamp(
    pipeline: str = PRIMARY_PIPELINE,
    session_factory: Any = None,
) -> datetime | None:
    """Finish time of the newest successful ETL run, read from the ``etl.etl_runs`` log.

    ETL runs execute in Celery workers while ``data_freshness_seconds`` is served
    by the API process, so the persisted run log is the only source both share.
    """
    from app.db.session import AsyncSessionLocal
    from app.models.etl_run import ETLRun

    factory = session_factory or AsyncSessionLocal
    async with factory() as session:
        latest = await session.scalar(
            select(func.max(ETLRun.finished_at)).where(
                ETLRun.pipeline == pipeline,
                ETLRun.status.in_(("succeeded", "success")),
            )
        )
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return latest


async def refresh_data_freshness(
    pipeline: str = PRIMARY_PIPELINE,
    session_factory: Any = None,
) -> DataFreshnessReport:
    """Recompute freshness from the ETL run log (falling back to in-process metrics)."""
    latest: datetime | None = None
    try:
        latest = await get_last_successful_run_timestamp(pipeline, session_factory)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not read last successful ETL run from database: %s", exc)
    if latest is not None:
        return _build_report(latest, "etl_runs")
    return evaluate_data_freshness(pipeline=pipeline)


async def run_freshness_refresher(
    interval_seconds: float = 60.0,
    pipeline: str = PRIMARY_PIPELINE,
) -> None:
    """Keep ``data_freshness_seconds`` current for Prometheus, independent of who polls the API."""
    while True:
        try:
            await refresh_data_freshness(pipeline)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Data freshness refresh failed", exc_info=True)
        await asyncio.sleep(interval_seconds)
