from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from app.domain.entities.raw_ingestion import RawIngestionEventRecord


class RawIngestionRepository(Protocol):
    """Contract for persisted raw ingestion events in staging."""

    def add_many(
        self,
        entities: list[RawIngestionEventRecord],
    ) -> list[RawIngestionEventRecord]:
        """Persist many raw ingestion rows."""

    def list_by_run_id(
        self,
        ingestion_run_id: str,
    ) -> Iterable[RawIngestionEventRecord]:
        """Return raw events captured by one ingestion run."""

    def list_by_source_resource(
        self,
        *,
        source: str,
        resource: str,
        limit: int = 100,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
    ) -> Iterable[RawIngestionEventRecord]:
        """Return raw events filtered by source/resource and optional time window."""
