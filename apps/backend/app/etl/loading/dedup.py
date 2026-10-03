from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ExistingRecordLookup(Protocol):
    """Returns the stored payload_hash for a natural_key (or None)."""

    def __call__(self, entity: str, natural_key: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class DedupDecision:
    action: str  # "insert" | "update" | "unchanged"
    natural_key: str
    entity: str


def decide_action(
    entity: str,
    natural_key: str,
    payload_hash: str,
    existing_hash: str | None,
) -> DedupDecision:
    """Classify a record before loading.

    - ``insert`` when there is no existing row.
    - ``unchanged`` when the existing hash matches (exact duplicate).
    - ``update`` when the natural key exists but the payload changed.
    """
    if existing_hash is None:
        return DedupDecision("insert", natural_key, entity)
    if existing_hash == payload_hash:
        return DedupDecision("unchanged", natural_key, entity)
    return DedupDecision("update", natural_key, entity)


def classify_batch(
    records: list[Any],
    lookup: ExistingRecordLookup,
) -> dict[str, list[Any]]:
    """Partition transformed records into insert/update/unchanged buckets.

    Each record must expose ``entity``, ``natural_key`` and ``payload_hash``
    attributes (i.e. ``TransformedRecord``).
    """
    buckets: dict[str, list[Any]] = {"insert": [], "update": [], "unchanged": []}
    for record in records:
        existing = lookup(record.entity, record.natural_key)
        decision = decide_action(
            record.entity,
            record.natural_key,
            record.payload_hash,
            existing,
        )
        buckets[decision.action].append(record)
    return buckets
