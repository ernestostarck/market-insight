from __future__ import annotations

from collections.abc import Iterable

from app.etl.dedup.engine import DeduplicationEngine
from app.etl.dedup.models import DedupResult
from app.etl.models import TransformedRecord


def partition_by_action(
    records: Iterable[TransformedRecord],
    result: DedupResult,
) -> dict[str, list[TransformedRecord]]:
    """Group records by their dedup action (insert/update/unchanged/conflict).

    The result decisions are aligned positionally with the incoming records
    produced by the engine's ``run`` (same order). Consumers use the buckets to
    drive loading: inserts/updates go to the loader, unchanged are skipped, and
    conflicts are routed to quarantine/audit.
    """
    records_list = list(records)
    buckets: dict[str, list[TransformedRecord]] = {
        "insert": [],
        "update": [],
        "unchanged": [],
        "conflict": [],
    }
    for record, decision in zip(records_list, result.decisions):
        buckets[decision.action].append(record)
    return buckets


def summarize_result(result: DedupResult) -> dict[str, int]:
    """Return a compact summary of a dedup pass suitable for metrics."""
    return result.summaries
