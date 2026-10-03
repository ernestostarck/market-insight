from datetime import date, datetime, timezone

import pytest
from app.etl.incremental.models import IncrementalCheckpoint
from app.etl.incremental.window import IncrementalPlanner


class _CheckpointLike:
    def __init__(self, marker: str | None) -> None:
        self.marker = marker


def _aware_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def test_no_checkpoint_produces_backfill_plan() -> None:
    planner = IncrementalPlanner(backfill_chunk_days=30)
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=None,
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-02-01"),
    )

    assert plan.mode == "backfill"
    assert plan.window is None
    assert plan.source == "chilecompra_api"
    assert plan.resource == "licitaciones"
    assert len(plan.backfill_windows) > 0
    assert plan.backfill_windows[0].start == _aware_iso("2026-01-01")
    assert plan.backfill_windows[-1].end == _aware_iso("2026-02-01")


def test_force_backfill_ignores_checkpoint() -> None:
    planner = IncrementalPlanner(backfill_chunk_days=30)
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=_CheckpointLike(marker="2026-05-01"),
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-02-01"),
        force_backfill=True,
    )

    assert plan.mode == "backfill"


def test_existing_checkpoint_produces_incremental_window() -> None:
    planner = IncrementalPlanner()
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=_CheckpointLike(marker="2026-08-01"),
        end_at=_aware_iso("2026-08-06"),
    )

    assert plan.mode == "incremental"
    assert plan.backfill_windows == []
    assert plan.window is not None
    assert plan.window.start == _aware_iso("2026-08-01")
    assert plan.window.end == _aware_iso("2026-08-06")


def test_invalid_marker_falls_back_to_backfill() -> None:
    planner = IncrementalPlanner()
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=_CheckpointLike(marker="not-a-date"),
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-02-01"),
    )

    assert plan.mode == "backfill"
    assert len(plan.backfill_windows) > 0


def test_history_start_after_end_raises() -> None:
    planner = IncrementalPlanner()
    with pytest.raises(ValueError):
        planner.build_plan(
            source="chilecompra_api",
            resource="licitaciones",
            checkpoint=None,
            history_start=date(2026, 3, 1),
            end_at=_aware_iso("2026-02-01"),
        )


def test_chunked_backfill_windows_cover_range() -> None:
    planner = IncrementalPlanner(backfill_chunk_days=10)
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=None,
        history_start=date(2026, 1, 1),
        end_at=_aware_iso("2026-01-25"),
    )

    chunks = plan.backfill_windows
    expected_days = (date(2026, 1, 25) - date(2026, 1, 1)).days + 1
    assert sum(c.day_count() for c in chunks) == expected_days
    assert chunks[0].start == _aware_iso("2026-01-01")
    assert chunks[-1].end == _aware_iso("2026-01-25")


def test_watermark_checkpoint_object_accepted() -> None:
    planner = IncrementalPlanner()
    checkpoint = IncrementalCheckpoint(
        source="chilecompra_api",
        resource="licitaciones",
        marker="2026-08-01",
        updated_at=_aware_iso("2026-08-01"),
        last_status="succeeded",
    )
    plan = planner.build_plan(
        source="chilecompra_api",
        resource="licitaciones",
        checkpoint=checkpoint,
        end_at=_aware_iso("2026-08-06"),
    )

    assert plan.mode == "incremental"
