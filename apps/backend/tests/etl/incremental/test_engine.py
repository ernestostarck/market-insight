from datetime import date, datetime, timezone

from app.etl.extraction.base import ExtractionWindow
from app.etl.incremental.checkpointer import InMemoryCheckpointStore
from app.etl.incremental.engine import IncrementalETL
from app.etl.incremental.models import (
    IncrementalCheckpoint,
    IncrementalLoadTrigger,
    IncrementalRunStatus,
)
from app.etl.incremental.window import IncrementalPlanner
from app.etl.models import ETLMetrics, ETLRunSummary, IngestionRunContext


class FakePipeline:
    """Records the windows it was asked to process and returns a summary."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[IngestionRunContext] = []

    async def run(
        self,
        *,
        run: IngestionRunContext,
        window: ExtractionWindow | None = None,
    ):
        self.calls.append(run)
        if self.fail:
            raise RuntimeError("boom")
        metrics = ETLMetrics(extracted=10, valid=9, invalid=1, inserted=9)
        return ETLRunSummary(run=run, metrics=metrics, quarantine_count=1)


def _aware_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _checkpoint(marker: str) -> IncrementalCheckpoint:
    return IncrementalCheckpoint(
        source="chilecompra_api",
        resource="licitaciones",
        marker=marker,
        updated_at=_aware_iso("2026-08-01"),
        last_status="succeeded",
    )


def _build_engine(
    *,
    fail: bool = False,
) -> tuple[IncrementalETL, FakePipeline, InMemoryCheckpointStore]:
    store = InMemoryCheckpointStore()
    pipeline = FakePipeline(fail=fail)
    engine = IncrementalETL(
        pipeline_factory=lambda: pipeline,
        checkpointer=store,
        planner=IncrementalPlanner(backfill_chunk_days=30),
        resource="licitaciones",
        source="chilecompra_api",
    )
    return engine, pipeline, store


async def test_incremental_run_advances_checkpoint_on_success() -> None:
    engine, pipeline, store = _build_engine()
    store.set(_checkpoint("2026-08-01"))

    run = await engine.run(end_at=_aware_iso("2026-08-06"))

    assert run.status == IncrementalRunStatus.SUCCEEDED
    assert run.trigger == IncrementalLoadTrigger.SCHEDULE
    assert len(pipeline.calls) == 1
    assert run.metrics["inserted"] == 9

    checkpoint = store.get(source="chilecompra_api", resource="licitaciones")
    assert checkpoint is not None
    assert checkpoint.marker == _aware_iso("2026-08-06").isoformat()


async def test_backfill_run_processes_all_chunks() -> None:
    engine, pipeline, store = _build_engine()

    run = await engine.run(
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-02-01"),
        trigger=IncrementalLoadTrigger.MANUAL,
    )

    assert run.status == IncrementalRunStatus.SUCCEEDED
    assert len(pipeline.calls) > 1  # chunked backfill
    assert run.metrics["inserted"] == 9 * len(pipeline.calls)

    checkpoint = store.get(source="chilecompra_api", resource="licitaciones")
    assert checkpoint is not None
    assert checkpoint.marker == _aware_iso("2026-02-01").isoformat()


async def test_failed_run_does_not_advance_checkpoint() -> None:
    engine, pipeline, store = _build_engine(fail=True)
    store.set(_checkpoint("2026-08-01"))

    run = await engine.run(end_at=_aware_iso("2026-08-06"))

    assert run.status == IncrementalRunStatus.FAILED
    assert run.error is not None

    checkpoint = store.get(source="chilecompra_api", resource="licitaciones")
    assert checkpoint is not None
    assert checkpoint.marker == "2026-08-01"  # unchanged


async def test_force_backfill_ignores_existing_checkpoint() -> None:
    engine, pipeline, store = _build_engine()
    store.set(_checkpoint("2026-08-01"))

    run = await engine.run(
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-02-01"),
        force_backfill=True,
    )

    assert run.status == IncrementalRunStatus.SUCCEEDED
    assert len(pipeline.calls) > 1
