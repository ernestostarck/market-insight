"""Celery jobs for ETL orchestration (Fase 3.11).

FastAPI must never run heavy ETL processes inline. Instead, the API (or a
scheduler) enqueues a job here; a Celery worker consumes it and executes the
incremental engine out-of-process, keeping the web tier responsive.

Public API
----------
* :func:`sync_resource` — run an incremental (or backfill) sync for one
  ``(source, resource)`` stream.
* :func:`sync_all` — tick several configured streams in one task.
* Convenience helpers to build a configured :class:`Celery` app and its beat
  schedule (see :mod:`app.etl.orchestration.scheduler`).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from app.etl.incremental import IncrementalETL
from app.etl.incremental.checkpointer import (
    CheckpointStore,
    SqlAlchemyCheckpointStore,
)
from app.etl.incremental.engine import PipelineRunner
from app.etl.incremental.models import IncrementalLoadTrigger, IncrementalRun
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.sdk import ChileCompraClient as ChileCompraSDK
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

#: Streams that are safe to sync under a scheduled/incremental run.
DEFAULT_RESOURCES: tuple[str, ...] = (
    "licitaciones",
    "ordenes_compra",
    "empresas",
    "contratos",
    "convenios_marco",
    "adjudicaciones",
)


def _sdk_client() -> ChileCompraSDK:
    """Build a ChileCompra SDK from application settings."""
    return ChileCompraSDK.from_config(ChileCompraConfig.from_settings())


def _checkpoint_store() -> CheckpointStore:
    """Return a durable checkpoint store backed by PostgreSQL.

    Imports are deferred (and the connection factory is lazy) so that loading
    this module inside tests does not require a live database.
    """
    from sqlalchemy import create_engine as _create

    from app.core.config import get_settings

    engine = _create(get_settings().database_url, pool_pre_ping=True)
    return SqlAlchemyCheckpointStore(lambda: engine.connect())


def _pipeline_factory(resource: str) -> Callable[[], PipelineRunner]:
    """Build a real ETL pipeline for `resource`: extracts from ChileCompra,
    stages raw payloads and loads transformed records into Postgres.

    `licitaciones` persists into `core.licitacion` via `CoreLicitacionLoader`
    (the canonical, Alembic-migrated table the rest of the app reads from).
    Other resources still fall back to an in-memory loader — they have no
    equivalent core.* loader yet; this is a known, separate gap.

    Imports are deferred, and the engine is created once here (not per window)
    so a backfill's multiple windows share one connection pool.
    """
    from sqlalchemy import create_engine as _create
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.etl.extraction.chilecompra import ChileCompraAPIDataSource
    from app.etl.ingestion.raw_ingestor import SqlAlchemyRawIngestor
    from app.etl.loading.base import RecordLoader
    from app.etl.loading.core_schema import CoreLicitacionLoader
    from app.etl.models import LoadResult
    from app.etl.orchestration.pipeline import ETLPipeline
    from app.etl.transformation.router import default_transformation_router
    from app.etl.validation.validators import default_validation_router
    from app.infrastructure.repositories.raw_ingestion_repository import (
        SqlAlchemyRawIngestionRepository,
    )

    engine = _create(get_settings().database_url, pool_pre_ping=True)

    class _InMemoryLoader(RecordLoader):
        def load(self, run, records):
            return LoadResult(inserted=len(records))

    def factory() -> ETLPipeline:
        source = ChileCompraAPIDataSource(_sdk_client(), resource=resource)
        raw_ingestor = SqlAlchemyRawIngestor(SqlAlchemyRawIngestionRepository(Session(engine)))
        loader = (
            CoreLicitacionLoader(lambda: engine.connect())
            if resource == "licitaciones"
            else _InMemoryLoader()
        )
        return ETLPipeline(
            source=source,
            raw_ingestor=raw_ingestor,
            validator=default_validation_router(),
            transformer=default_transformation_router(),
            loader=loader,
        )

    return factory


def _run_incremental(
    *,
    resource: str,
    source: str = "chilecompra_api",
    history_start: date | None = None,
    end_at: datetime | None = None,
    force_backfill: bool = False,
    trigger: IncrementalLoadTrigger = IncrementalLoadTrigger.SCHEDULE,
) -> IncrementalRun:
    """Execute an incremental ``IncrementalETL`` run synchronously (for Celery)."""
    engine = IncrementalETL(
        pipeline_factory=_pipeline_factory(resource),
        checkpointer=_checkpoint_store(),
        resource=resource,
        source=source,
    )
    return asyncio.run(
        engine.run(
            history_start=history_start,
            end_at=end_at,
            force_backfill=force_backfill,
            trigger=trigger,
        )
    )


def _sync_one_resource(
    *,
    resource: str,
    source: str = "chilecompra_api",
    force_backfill: bool = False,
    history_start: str | None = None,
    end_at: str | None = None,
) -> dict[str, Any]:
    """Run a single incremental sync and return a serializable status dict.

    Extracted from the Celery task so it can be reused by the batch task and
    tested without a live broker.
    """
    if resource not in DEFAULT_RESOURCES:
        raise ValueError(f"Unsupported resource for sync: {resource!r}")

    parsed_start = date.fromisoformat(history_start) if history_start else None
    parsed_end = datetime.fromisoformat(end_at) if end_at else None

    import time

    from app.monitoring.etl import record_sync_outcome, record_sync_start

    started_at = datetime.now(UTC)
    t0 = time.perf_counter()
    record_sync_start(pipeline=resource, source=source)

    try:
        run = _run_incremental(
            resource=resource,
            source=source,
            history_start=parsed_start,
            end_at=parsed_end,
            force_backfill=force_backfill,
            trigger=IncrementalLoadTrigger.SCHEDULE,
        )
        duration_s = time.perf_counter() - t0
        finished_at = datetime.now(UTC)
        record_sync_outcome(
            run_id=run.run_id,
            pipeline=resource,
            source=source,
            status=run.status.value,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_s,
            metrics=run.metrics,
            error=run.error,
        )
        return {
            "status": run.status.value,
            "run_id": run.run_id,
            "source": source,
            "resource": resource,
            "metrics": run.metrics,
            "error": run.error,
        }
    except Exception as exc:
        duration_s = time.perf_counter() - t0
        finished_at = datetime.now(UTC)
        record_sync_outcome(
            run_id=f"etl-{resource}-failed",
            pipeline=resource,
            source=source,
            status="failed",
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_s,
            error=str(exc),
        )
        raise


@celery_app.task(
    name="app.etl.orchestration.jobs.sync_resource", bind=True, max_retries=3
)
def sync_resource(
    self,
    resource: str,
    *,
    source: str = "chilecompra_api",
    force_backfill: bool = False,
    history_start: str | None = None,
    end_at: str | None = None,
) -> dict[str, Any]:
    """Synchronize a single ``(source, resource)`` stream via the incremental engine.

    This is the low-level job that the scheduler and the high-level tasks call.
    It is idempotent at the watermark level: the engine only advances the
    checkpoint when every planned window succeeds, so a re-run never loses data.
    """
    try:
        return _sync_one_resource(
            resource=resource,
            source=source,
            force_backfill=force_backfill,
            history_start=history_start,
            end_at=end_at,
        )
    except Exception as exc:  # -- retry with backoff (Fase 3.12) -- #
        logger.exception("sync_resource failed for %s/%s", source, resource)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


@celery_app.task(name="app.etl.orchestration.jobs.sync_all")
def sync_all_resources(
    *,
    resources: tuple[str, ...] | None = None,
    source: str = "chilecompra_api",
) -> dict[str, Any]:
    """Tick several configured streams in sequence.

    Useful for a manual "sync everything" or a periodic full refresh. Each
    resource is delegated to :func:`_sync_one_resource` so failures are
    contained per stream.
    """
    targets = resources or DEFAULT_RESOURCES
    results: dict[str, Any] = {}
    for resource in targets:
        results[resource] = _sync_one_resource(resource=resource, source=source)
    return {"source": source, "resources": results}


@celery_app.task(
    name="app.etl.orchestration.jobs.enrich_licitacion_detail", bind=True, max_retries=3,
)
def enrich_licitacion_detail(self, codigo: str) -> dict[str, Any]:
    """On-demand detail fetch for one licitacion: Items, Descripcion, full
    Organismo (Comprador/Fechas) — none of which the daily bulk sync fetches
    (see `_pipeline_factory`). Dispatched one licitacion at a time, not on a
    beat schedule, to avoid multiplying the daily ChileCompra API volume.
    """
    from sqlalchemy import create_engine as _create

    from app.core.config import get_settings
    from app.etl.enrichment import enrich_licitacion_detail as _enrich
    from app.etl.loading.core_schema import (
        CoreLicitacionItemLoader,
        CoreLicitacionLoader,
    )

    try:
        engine = _create(get_settings().database_url, pool_pre_ping=True)
        result = asyncio.run(
            _enrich(
                codigo,
                client=_sdk_client(),
                licitacion_loader=CoreLicitacionLoader(lambda: engine.connect()),
                item_loader=CoreLicitacionItemLoader(lambda: engine.connect()),
                connection_factory=lambda: engine.connect(),
            )
        )
        return {"codigo": result.codigo, "found": result.found, "items_upserted": result.items_upserted}
    except Exception as exc:
        logger.exception("enrich_licitacion_detail failed for codigo=%s", codigo)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


# Alias kept for backward compatibility with the legacy worker namespace.
sync_licitaciones = sync_resource


__all__ = [
    "DEFAULT_RESOURCES",
    "enrich_licitacion_detail",
    "sync_all_resources",
    "sync_licitaciones",
    "sync_resource",
]
