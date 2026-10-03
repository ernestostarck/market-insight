"""ETL monitoring service and persistence tracker (Fase 8.7)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.etl_run import ETLRun
from app.monitoring.metrics import (
    record_etl_run_failure,
    record_etl_run_start,
    record_etl_run_success,
)

logger = logging.getLogger(__name__)


def record_sync_start(
    pipeline: str,
    source: str = "chilecompra_api",
    trigger: str = "schedule",
    run_id: str | None = None,
) -> str:
    """Record run start in Prometheus metrics and return run_id."""
    effective_run_id = run_id or f"etl-{pipeline}-{uuid4().hex[:12]}"
    record_etl_run_start(pipeline=pipeline)
    return effective_run_id


def record_sync_outcome(
    *,
    run_id: str,
    pipeline: str,
    source: str = "chilecompra_api",
    trigger: str = "schedule",
    status: str,
    started_at: datetime,
    finished_at: datetime,
    duration_seconds: float,
    metrics: dict[str, int] | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Update Prometheus metrics and asynchronously persist to database."""
    counts = metrics or {}
    records_read = counts.get("extracted", 0)
    records_inserted = counts.get("inserted", 0)
    records_updated = counts.get("updated", 0)
    records_failed = counts.get("failed", 0)
    error_count = 1 if (error or status == "failed") else records_failed

    # 1. Update Prometheus metrics
    if status == "succeeded" or status == "success":
        record_etl_run_success(
            pipeline=pipeline,
            duration_seconds=duration_seconds,
            records_read=records_read,
            records_inserted=records_inserted,
            records_updated=records_updated,
            records_failed=records_failed,
        )
    else:
        record_etl_run_failure(
            pipeline=pipeline,
            duration_seconds=duration_seconds,
            records_failed=records_failed or 1,
        )

    # 2. Persist to PostgreSQL if available (best effort / non-blocking)
    try:
        from sqlalchemy import create_engine

        engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        with Session(engine) as session:
            run_row = ETLRun(
                run_id=run_id,
                pipeline=pipeline,
                source=source,
                trigger=trigger,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=round(duration_seconds, 3),
                records_read=records_read,
                records_inserted=records_inserted,
                records_updated=records_updated,
                records_failed=records_failed,
                error_count=error_count,
                error_message=error,
                extra=extra or {},
            )
            session.merge(run_row)
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not persist ETLRun %s to database: %s", run_id, exc)


async def get_recent_etl_runs(
    pipeline: str | None = None,
    limit: int = 50,
) -> list[ETLRun]:
    """Fetch recent ETL pipeline runs from the database."""
    async with AsyncSessionLocal() as session:
        query = select(ETLRun).order_by(ETLRun.started_at.desc()).limit(limit)
        if pipeline:
            query = query.where(ETLRun.pipeline == pipeline)
        result = await session.execute(query)
        return list(result.scalars().all())
