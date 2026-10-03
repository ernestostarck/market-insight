from __future__ import annotations

import pytest
from app.etl.dedup.engine import DeduplicationEngine
from app.etl.dedup.models import DedupPolicy
from app.etl.dedup.repository import (
    ExistingRecord,
    InMemoryDedupRepository,
)
from app.etl.dedup.service import partition_by_action, summarize_result
from app.etl.models import TransformedRecord


def _record(
    entity: str,
    natural_key: str,
    payload_hash: str,
    *,
    source_id: str | None = None,
    payload: dict | None = None,
) -> TransformedRecord:
    return TransformedRecord(
        entity=entity,
        natural_key=natural_key,
        payload=payload or {"key": natural_key},
        source_id=source_id or natural_key,
        payload_hash=payload_hash,
    )


def test_classifies_insert_unchanged_and_update() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-1-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-1-LP26",
                payload_hash="hash-old",
            ),
            "licitacion:chilecompra:1000-2-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-2-LP26",
                payload_hash="hash-same",
            ),
        }
    )
    engine = DeduplicationEngine(repo)
    records = [
        # existing row but different hash -> update
        _record(
            "licitacion",
            "licitacion:chilecompra:1000-1-LP26",
            "hash-new",
        ),
        # existing row same hash -> unchanged
        _record(
            "licitacion",
            "licitacion:chilecompra:1000-2-LP26",
            "hash-same",
        ),
        # new row -> insert
        _record(
            "licitacion",
            "licitacion:chilecompra:1000-3-LP26",
            "hash-insert",
        ),
    ]

    result = engine.run(records)

    summaries = result.summaries
    assert summaries == {"insert": 1, "update": 1, "unchanged": 1, "conflict": 0}


def test_missing_stored_hash_treated_as_new_by_default() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-9-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-9-LP26",
                payload_hash=None,
            ),
        }
    )
    engine = DeduplicationEngine(repo)
    result = engine.run(
        [
            _record(
                "licitacion",
                "licitacion:chilecompra:1000-9-LP26",
                "hash-any",
            )
        ]
    )

    assert result.summaries["insert"] == 1


def test_missing_stored_hash_falls_back_to_update_when_disabled() -> None:
    """With treat_missing_hash_as_new disabled a missing stored hash cannot be
    proven equal, so the engine falls back to a safe ``update``."""
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-9-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-9-LP26",
                payload_hash=None,
            ),
        }
    )
    engine = DeduplicationEngine(
        repo,
        policy=DedupPolicy(treat_missing_hash_as_new=False),
    )
    result = engine.run(
        [
            _record(
                "licitacion",
                "licitacion:chilecompra:1000-9-LP26",
                "hash-any",
            )
        ]
    )

    assert result.summaries["update"] == 1
    assert result.updates[0].existing_hash is None


def test_duplicate_natural_keys_reported_as_conflict() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-1-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-1-LP26",
                payload_hash="hash-old",
            ),
        }
    )
    engine = DeduplicationEngine(repo)
    records = [
        _record(
            "licitacion",
            "licitacion:chilecompra:1000-1-LP26",
            "hash-a",
        ),
        _record(
            "licitacion",
            "licitacion:chilecompra:1000-1-LP26",
            "hash-b",
        ),
    ]

    result = engine.run(records)

    assert result.summaries["conflict"] == 1
    conflict = result.conflicts[0]
    assert conflict.collisions == 2
    assert conflict.existing_hash == "hash-old"


def test_conflict_detection_can_be_disabled() -> None:
    repo = InMemoryDedupRepository()
    engine = DeduplicationEngine(
        repo,
        policy=DedupPolicy(report_conflicts=False),
    )
    records = [
        _record("licitacion", "licitacion:chilecompra:1000-1-LP26", "hash-a"),
        _record("licitacion", "licitacion:chilecompra:1000-1-LP26", "hash-b"),
    ]

    result = engine.run(records)

    assert result.summaries["conflict"] == 0
    assert result.summaries["insert"] == 2


def test_partition_by_action_splits_records() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-2-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-2-LP26",
                payload_hash="hash-same",
            ),
        }
    )
    engine = DeduplicationEngine(repo)
    records = [
        _record("licitacion", "licitacion:chilecompra:1000-1-LP26", "hash-new"),
        _record("licitacion", "licitacion:chilecompra:1000-2-LP26", "hash-same"),
    ]
    result = engine.run(records)

    buckets = partition_by_action(records, result)

    assert len(buckets["insert"]) == 1
    assert buckets["insert"][0].natural_key == "licitacion:chilecompra:1000-1-LP26"
    assert len(buckets["unchanged"]) == 1
    assert len(buckets["update"]) == 0
    assert len(buckets["conflict"]) == 0


def test_partition_keeps_record_identity_and_order() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-2-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-2-LP26",
                payload_hash="old",
            ),
        }
    )
    engine = DeduplicationEngine(repo)
    records = [
        # existing row, different hash -> update
        _record("licitacion", "licitacion:chilecompra:1000-2-LP26", "new-hash"),
        # new row -> insert
        _record("licitacion", "licitacion:chilecompra:1000-3-LP26", "insert-hash"),
    ]
    result = engine.run(records)
    buckets = partition_by_action(records, result)

    assert buckets["update"][0].natural_key == "licitacion:chilecompra:1000-2-LP26"
    assert buckets["update"][0].payload_hash == "new-hash"
    assert buckets["insert"][0].natural_key == "licitacion:chilecompra:1000-3-LP26"
    assert buckets["insert"][0].payload_hash == "insert-hash"


def test_without_conflict_reporting_same_key_emits_per_record() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-2-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-2-LP26",
                payload_hash="old",
            ),
        }
    )
    engine = DeduplicationEngine(
        repo,
        policy=DedupPolicy(report_conflicts=False),
    )
    records = [
        _record("licitacion", "licitacion:chilecompra:1000-2-LP26", "a"),
        _record("licitacion", "licitacion:chilecompra:1000-2-LP26", "b"),
    ]
    result = engine.run(records)

    # Two decisions, both updates (each differs from stored "old").
    assert result.summaries["conflict"] == 0
    assert result.summaries["update"] == 2


def test_summarize_result_returns_counts() -> None:
    repo = InMemoryDedupRepository()
    engine = DeduplicationEngine(repo)
    records = [
        _record("licitacion", "licitacion:chilecompra:1", "hash-1"),
        _record("licitacion", "licitacion:chilecompra:2", "hash-2"),
    ]
    result = engine.run(records)

    assert summarize_result(result)["insert"] == 2
    assert summarize_result(result)["unchanged"] == 0


def test_engine_handles_multiple_entities_in_one_batch() -> None:
    repo = InMemoryDedupRepository(
        {
            "empresa:chilecompra:EMPRESA-1": ExistingRecord(
                natural_key="empresa:chilecompra:EMPRESA-1",
                payload_hash="old",
            )
        }
    )
    engine = DeduplicationEngine(repo)
    records = [
        _record("licitacion", "licitacion:chilecompra:1000-2-LP26", "hash-l"),
        _record("empresa", "empresa:chilecompra:EMPRESA-1", "new-emp"),
        _record("empresa", "empresa:chilecompra:EMPRESA-2", "emp-2"),
    ]

    result = engine.run(records)

    assert result.summaries["insert"] == 2  # 1 licitacion + 1 empresa
    assert result.summaries["update"] == 1  # EMPRESA-1
    assert result.summaries["unchanged"] == 0
