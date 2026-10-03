from collections.abc import Iterable
from datetime import date
from typing import Protocol

from app.domain.entities.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRecord,
)


class AdjudicacionAnalyticsRepository(Protocol):
    """Contract for persisted adjudicaciones analytics snapshots."""

    def add_many(
        self, entities: list[AdjudicacionAnalyticsSnapshotRecord]
    ) -> list[AdjudicacionAnalyticsSnapshotRecord]:
        """Persist many snapshot rows."""

    def list_by_external_id(
        self, external_id: str, limit: int = 50
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        """Return historical snapshots for one adjudicacion."""

    def get_latest(
        self, external_id: str
    ) -> AdjudicacionAnalyticsSnapshotRecord | None:
        """Return the latest snapshot for one adjudicacion."""

    def list_by_snapshot_date(
        self, snapshot_date: date
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        """Return all snapshot rows captured at one snapshot date."""

    def list_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        """Return snapshot rows between two dates (inclusive)."""
