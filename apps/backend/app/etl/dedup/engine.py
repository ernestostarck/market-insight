from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.etl.dedup.models import (
    DedupDecision,
    DedupPolicy,
    DedupResult,
)
from app.etl.dedup.repository import DedupRepository
from app.etl.models import TransformedRecord


class DeduplicationEngine:
    """Classifies transformed records against persisted state.

    For each record it groups by entity and natural key, then consults the
    repository. The classification logic:

    - no existing row                  -> ``insert``
    - existing row, incoming == stored -> ``unchanged``
    - existing row, incoming != stored -> ``update``
    - multiple occurrences / policy    -> ``conflict`` (guards integrity)
    """

    def __init__(
        self,
        repository: DedupRepository,
        policy: DedupPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or DedupPolicy()

    def run(self, records: Iterable[TransformedRecord]) -> DedupResult:
        decisions: list[DedupDecision] = []
        grouped = self._group_by_key(records)

        # Regroup by entity for one batch lookup per entity.
        by_entity: dict[str, list[tuple[str, list[TransformedRecord]]]] = defaultdict(
            list
        )
        for (entity, _key), items in grouped.items():
            by_entity[entity].append((items[0].natural_key, items))

        for entity, groups in by_entity.items():
            all_keys = [key for key, _ in groups]
            existing = self._repository.get_existing_batch(entity, all_keys)
            for key, items in groups:
                decisions.extend(self._decide(entity, key, items, existing.get(key)))

        return DedupResult(decisions=decisions)

    def _group_by_key(self, records) -> dict[tuple[str, str], list[TransformedRecord]]:
        grouped: dict[tuple[str, str], list[TransformedRecord]] = defaultdict(list)
        for record in records:
            grouped[(record.entity, record.natural_key)].append(record)
        return grouped

    def _decide(
        self,
        entity: str,
        natural_key: str,
        items: list[TransformedRecord],
        existing,
    ) -> list[DedupDecision]:
        should_report_conflicts = (
            self._policy.report_conflicts and self._policy.conflict_threshold
        )
        if should_report_conflicts and len(items) > self._policy.conflict_threshold:
            return [
                DedupDecision(
                    action="conflict",
                    entity=entity,
                    natural_key=natural_key,
                    incoming_hash=items[0].payload_hash,
                    existing_hash=existing.payload_hash if existing else None,
                    collisions=len(items),
                )
            ]

        decisions: list[DedupDecision] = []
        for item in items:
            decisions.append(self._decide_single(entity, natural_key, item, existing))
        return decisions

    def _decide_single(
        self,
        entity: str,
        natural_key: str,
        item,
        existing,
    ) -> DedupDecision:
        if existing is None:
            return DedupDecision(
                action="insert",
                entity=entity,
                natural_key=natural_key,
                incoming_hash=item.payload_hash,
            )

        stored_hash = existing.payload_hash
        if stored_hash is None and self._policy.treat_missing_hash_as_new:
            return DedupDecision(
                action="insert",
                entity=entity,
                natural_key=natural_key,
                incoming_hash=item.payload_hash,
            )

        if stored_hash == item.payload_hash:
            return DedupDecision(
                action="unchanged",
                entity=entity,
                natural_key=natural_key,
                incoming_hash=item.payload_hash,
                existing_hash=stored_hash,
            )
        return DedupDecision(
            action="update",
            entity=entity,
            natural_key=natural_key,
            incoming_hash=item.payload_hash,
            existing_hash=stored_hash,
        )
