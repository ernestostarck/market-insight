from datetime import datetime, timezone

from app.etl.incremental.checkpointer import (
    IncrementalCheckpointer,
    InMemoryCheckpointStore,
)
from app.etl.incremental.models import IncrementalCheckpoint


def _aware_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def test_in_memory_store_round_trip() -> None:
    store = InMemoryCheckpointStore()
    checkpoint = IncrementalCheckpoint(
        source="chilecompra_api",
        resource="licitaciones",
        marker="2026-08-01",
        updated_at=_aware_iso("2026-08-01"),
        last_status="succeeded",
    )
    store.set(checkpoint)

    fetched = store.get(source="chilecompra_api", resource="licitaciones")
    assert fetched is not None
    assert fetched.marker == "2026-08-01"
    assert fetched.last_status == "succeeded"


def test_in_memory_store_get_missing_returns_none() -> None:
    store = InMemoryCheckpointStore()
    assert store.get(source="x", resource="y") is None


def test_in_memory_store_reset() -> None:
    store = InMemoryCheckpointStore()
    checkpoint = IncrementalCheckpoint(
        source="s",
        resource="r",
        marker="m",
        updated_at=_aware_iso("2026-08-01"),
    )
    store.set(checkpoint)
    store.reset(source="s", resource="r")
    assert store.get(source="s", resource="r") is None


def test_incremental_checkpointer_advance_persists_marker() -> None:
    store = InMemoryCheckpointStore()
    checkpointer = IncrementalCheckpointer(store)

    checkpointer.advance(
        source="chilecompra_api",
        resource="licitaciones",
        marker="2026-08-06",
        status="succeeded",
        updated_at=_aware_iso("2026-08-06"),
    )

    fetched = checkpointer.get(source="chilecompra_api", resource="licitaciones")
    assert fetched is not None
    assert fetched.marker == "2026-08-06"
    assert fetched.last_status == "succeeded"


def test_incremental_checkpointer_get_missing() -> None:
    checkpointer = IncrementalCheckpointer(InMemoryCheckpointStore())
    assert checkpointer.get(source="chilecompra_api", resource="licitaciones") is None


def test_incremental_checkpointer_reset() -> None:
    store = InMemoryCheckpointStore()
    checkpointer = IncrementalCheckpointer(store)
    checkpointer.advance(
        source="s",
        resource="r",
        marker="m",
        updated_at=_aware_iso("2026-08-01"),
    )
    checkpointer.reset(source="s", resource="r")
    assert checkpointer.get(source="s", resource="r") is None
