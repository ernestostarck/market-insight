"""Incremental ETL engine.

The engine glues together the parts of the architecture (extract, validate,
transform, load, quality) and adds the incremental concern: it resolves a plan
from the current checkpoint, executes each planned window through a pipeline,
and advances the checkpoint only after a successful run so that a failure never
losses progress or marks work as done that wasn't.

:class:`IncrementalETL` is the public entry point. It is also referenced from
``worker/tasks.py`` (``from app.etl.incremental import IncrementalETL``), so the
package ``app.etl.incremental`` re-exports it via ``__init__``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol

from app.etl.audit.lineage import audit_from_incremental
from app.etl.audit.reporter import AuditReporter
from app.etl.extraction.base import ExtractionWindow
from app.etl.incremental.checkpointer import (
    CheckpointStore,
    IncrementalCheckpointer,
    InMemoryCheckpointStore,
)
from app.etl.incremental.models import (
    IncrementalLoadTrigger,
    IncrementalPlan,
    IncrementalRun,
    IncrementalWindow,
)
from app.etl.incremental.window import IncrementalPlanner
from app.etl.models import IngestionRunContext

logger = logging.getLogger(__name__)


class PipelineRunner(Protocol):
    """Structural contract expected from an ETL pipeline component."""

    async def run(
        self, *, run: IngestionRunContext, window: ExtractionWindow | None = None
    ) -> Any: ...


class IncrementalETL:
    """Runs incremental / backfill loads over a single (source, resource) stream.

    The engine is deliberately wired from components (planner, pipeline factory,
    checkpointer) so it stays storage-agnostic and testable.
    """

    def __init__(
        self,
        client: Any | None = None,
        *,
        pipeline_factory: Callable[[], PipelineRunner] | None = None,
        checkpointer: CheckpointStore | IncrementalCheckpointer | None = None,
        planner: IncrementalPlanner | None = None,
        resource: str = "licitaciones",
        source: str = "chilecompra_api",
        audit_reporter: AuditReporter | None = None,
    ) -> None:
        """Build an incremental engine.

        Two wiring styles are supported:

        * **Modern**: pass ``pipeline_factory`` and ``checkpointer`` explicitly
          (recommended, fully testable).
        * **Legacy**: pass a ``client`` (the services-layer ``ChileCompraClient``
          has ``base_url``/``api_key``) and a default pipeline targeting the
          given ``resource`` is wired lazily. Kept for ``worker/tasks.py``.
        """
        if pipeline_factory is None:
            if client is None:
                raise TypeError(
                    "IncrementalETL requires `client` (legacy) or `pipeline_factory`"
                )
            pipeline_factory = self._default_pipeline_factory(client, resource=resource)
        self._pipeline_factory = pipeline_factory
        if checkpointer is None:
            checkpointer = InMemoryCheckpointStore()
        resolved_checkpointer: CheckpointStore | IncrementalCheckpointer = checkpointer
        self._checkpointer = (
            resolved_checkpointer
            if isinstance(resolved_checkpointer, IncrementalCheckpointer)
            else IncrementalCheckpointer(resolved_checkpointer)
        )
        self._planner = planner or IncrementalPlanner()
        self._resource = resource
        self._source = source
        self._audit_reporter = audit_reporter

    @staticmethod
    def _default_pipeline_factory(client: Any, *, resource: str):
        """Build a working ETL pipeline for ``resource`` from a legacy client.

        Imports are deferred to keep the package import-light and re-usable, and
        to avoid circular imports at module load time.
        """
        from app.etl.extraction.chilecompra import ChileCompraAPIDataSource
        from app.etl.ingestion.raw_ingestor import InMemoryRawIngestor
        from app.etl.loading.base import RecordLoader
        from app.etl.models import LoadResult
        from app.etl.orchestration.pipeline import ETLPipeline
        from app.etl.transformation.router import default_transformation_router
        from app.etl.validation.validators import default_validation_router
        from app.integrations.chilecompra.config import ChileCompraConfig
        from app.integrations.chilecompra.sdk import ChileCompraClient as SDKClient

        base_url = getattr(client, "base_url", None)
        api_key = getattr(client, "api_key", None)

        class _InMemoryLoader(RecordLoader):
            def __init__(self) -> None:
                self.items: list[object] = []

            def load(self, run, records):
                self.items.extend(records)
                return LoadResult(inserted=len(records))

        def _factory() -> ETLPipeline:
            config = ChileCompraConfig(
                api_url=base_url or "",
                api_ticket=api_key or "",
            )
            sdk = SDKClient.from_config(config)
            source = ChileCompraAPIDataSource(sdk, resource=resource)
            return ETLPipeline(
                source=source,
                raw_ingestor=InMemoryRawIngestor(),
                validator=default_validation_router(),
                transformer=default_transformation_router(),
                loader=_InMemoryLoader(),
            )

        return _factory

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def run(
        self,
        *,
        history_start=None,
        end_at: datetime | None = None,
        trigger: IncrementalLoadTrigger = IncrementalLoadTrigger.SCHEDULE,
        force_backfill: bool = False,
        run_id: str | None = None,
    ) -> IncrementalRun:
        """Execute an incremental (or forced backfill) load.

        The checkpoint is only advanced when every planned window succeeds.
        """
        checkpoint = self._checkpointer.get(
            source=self._source, resource=self._resource
        )
        plan = self._planner.build_plan(
            source=self._source,
            resource=self._resource,
            checkpoint=checkpoint,
            history_start=history_start,
            end_at=end_at,
            force_backfill=force_backfill,
        )

        run = IncrementalRun(
            source=self._source,
            resource=self._resource,
            run_id=run_id or _new_run_id(self._source, self._resource),
            window=self._first_window(plan),
            trigger=trigger,
        )
        run.mark_started()

        try:
            for window in self._iterative_windows(plan):
                summary = await self._run_window(run, plan, window)
                run.metrics = _accumulate(run.metrics, _metrics_of(summary))
                run.summary = summary
            self._advance_checkpoint(plan)
            run.mark_succeeded(summary=run.summary)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Incremental run failed for %s/%s", self._source, self._resource
            )
            run.mark_failed(str(exc))

        if self._audit_reporter is not None:
            audit = audit_from_incremental(
                run,
                summary=run.summary,
                endpoint=_endpoint_for(self._resource),
            )
            self._audit_reporter.emit(audit)
        return run

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _iterative_windows(self, plan: IncrementalPlan):
        if plan.mode == "incremental":
            if plan.window is not None:
                yield plan.window
            return
        yield from plan.backfill_windows

    def _first_window(self, plan: IncrementalPlan) -> IncrementalWindow | None:
        if plan.mode == "incremental":
            return plan.window
        return plan.backfill_windows[0] if plan.backfill_windows else None

    async def _run_window(
        self,
        run: IncrementalRun,
        plan: IncrementalPlan,
        window: IncrementalWindow | None,
    ):
        pipeline = self._pipeline_factory()
        ctx = IngestionRunContext(
            ingestion_run_id=run.run_id,
            source=self._source,
            resource=self._resource,
            pipeline_version=_pipeline_version(),
            started_at=run.started_at or datetime.now(timezone.utc),
            params=_window_params(plan, window),
        )
        return await pipeline.run(run=ctx, window=_extraction_window(window))

    def _advance_checkpoint(self, plan: IncrementalPlan) -> None:
        if plan.mode == "incremental":
            marker = _marker_of(plan.window)
        elif plan.backfill_windows:
            marker = _marker_of(plan.backfill_windows[-1])
        else:
            marker = None
        self._checkpointer.advance(
            source=self._source,
            resource=self._resource,
            marker=marker,
            status="succeeded",
        )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_PIPELINE_VERSION = "0.1.0"

#: Maps an ETL resource to the ChileCompra endpoint that feeds it.
_RESOURCE_ENDPOINTS: dict[str, str] = {
    "licitaciones": "/licitaciones.json",
    "licitaciones_historicas": "/licitaciones.json",
    "ordenes_compra": "/ordenescompra.json",
    "ordenes_compra_historicas": "/ordenescompra.json",
    "empresas": "/empresas.json",
    "empresas_historicas": "/empresas.json",
    "proveedores": "/empresas.json",
    "contratos": "/contratos.json",
    "convenios_marco": "/conveniomarco.json",
    "adjudicaciones": "/adjudicaciones.json",
}


def _endpoint_for(resource: str) -> str | None:
    """Return the ChileCompra endpoint for an ETL resource (or None)."""
    return _RESOURCE_ENDPOINTS.get(resource)


def _new_run_id(source: str, resource: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"ETL-{stamp}-{source}-{resource}"


def _pipeline_version() -> str:
    return _PIPELINE_VERSION


def _window_params(plan: IncrementalPlan, window: IncrementalWindow | None) -> dict:
    if window is None:
        return {"mode": plan.mode}
    return {
        "mode": plan.mode,
        "window_start": window.start.isoformat() if window.start else None,
        "window_end": window.end.isoformat() if window.end else None,
    }


def _extraction_window(window: IncrementalWindow | None) -> ExtractionWindow | None:
    if window is None:
        return None
    return ExtractionWindow(start_at=window.start, end_at=window.end)


def _marker_of(window: IncrementalWindow | None) -> str | None:
    if window is None or window.end is None:
        return None
    return window.end.isoformat()


def _metrics_of(summary) -> dict:
    metrics = getattr(summary, "metrics", None)
    if metrics is None:
        return {}
    keys = (
        "extracted",
        "raw_stored",
        "valid",
        "invalid",
        "transformed",
        "inserted",
        "updated",
        "unchanged",
        "failed",
    )
    return {key: getattr(metrics, key, 0) for key in keys}


def _accumulate(acc: dict, metrics: dict) -> dict:
    for key, value in metrics.items():
        acc[key] = acc.get(key, 0) + value
    return acc
