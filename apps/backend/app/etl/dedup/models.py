from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DedupDecision:
    """Outcome of deduplicating a single transformed record."""

    action: str  # "insert" | "update" | "unchanged" | "conflict"
    entity: str
    natural_key: str
    incoming_hash: str
    existing_hash: str | None = None
    # For conflict detection: how many rows shared the same natural key.
    collisions: int = 0

    @property
    def is_mutation(self) -> bool:
        return self.action in ("insert", "update")


@dataclass(slots=True)
class DedupResult:
    """Aggregate result of a deduplication pass over a batch."""

    decisions: list[DedupDecision] = field(default_factory=list)

    @property
    def inserts(self) -> list[DedupDecision]:
        return [d for d in self.decisions if d.action == "insert"]

    @property
    def updates(self) -> list[DedupDecision]:
        return [d for d in self.decisions if d.action == "update"]

    @property
    def unchanged(self) -> list[DedupDecision]:
        return [d for d in self.decisions if d.action == "unchanged"]

    @property
    def conflicts(self) -> list[DedupDecision]:
        return [d for d in self.decisions if d.action == "conflict"]

    @property
    def total(self) -> int:
        return len(self.decisions)

    @property
    def summaries(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "insert": 0,
            "update": 0,
            "unchanged": 0,
            "conflict": 0,
        }
        for decision in self.decisions:
            counts[decision.action] += 1
        return counts


@dataclass(slots=True)
class DedupPolicy:
    """Configuration knobs for the deduplication engine.

    - ``treat_missing_hash_as_new``: when a stored row lacks a payload_hash,
      decide based on existence rather than comparing digests.
    - ``report_conflicts``: count duplicate natural keys as ``conflict`` instead
      of silently choosing one; protects referential integrity for 3.12.
    """

    treat_missing_hash_as_new: bool = True
    report_conflicts: bool = True
    conflict_threshold: int = 1
