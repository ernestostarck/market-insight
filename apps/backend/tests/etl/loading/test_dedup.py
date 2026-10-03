from __future__ import annotations

from app.etl.loading.dedup import classify_batch, decide_action
from app.etl.models import TransformedRecord


def test_decide_action_insert_when_no_existing_hash() -> None:
    decision = decide_action("licitacion", "key-1", "hash-new", None)

    assert decision.action == "insert"


def test_decide_action_unchanged_when_hash_matches() -> None:
    decision = decide_action("licitacion", "key-1", "hash-x", "hash-x")

    assert decision.action == "unchanged"


def test_decide_action_update_when_hash_differs() -> None:
    decision = decide_action("licitacion", "key-1", "hash-new", "hash-old")

    assert decision.action == "update"


def _record(entity, key, payload_hash) -> TransformedRecord:
    return TransformedRecord(
        entity=entity,
        natural_key=key,
        payload={"external_id": key},
        source_id=key,
        payload_hash=payload_hash,
    )


def test_classify_batch_partitions_records() -> None:
    records = [
        _record("licitacion", "a", "h1"),
        _record("licitacion", "b", "h1"),
        _record("licitacion", "c", "h3"),
    ]
    existing = {
        ("licitacion", "b"): "h1",  # unchanged
        ("licitacion", "c"): "h-old",  # update
    }

    def lookup(entity, natural_key):
        return existing.get((entity, natural_key))

    buckets = classify_batch(records, lookup)

    assert [r.natural_key for r in buckets["insert"]] == ["a"]
    assert [r.natural_key for r in buckets["unchanged"]] == ["b"]
    assert [r.natural_key for r in buckets["update"]] == ["c"]


def test_classify_batch_empty() -> None:
    def lookup(entity: str, natural_key: str) -> str | None:
        return None

    buckets = classify_batch([], lookup)

    assert buckets == {"insert": [], "update": [], "unchanged": []}
