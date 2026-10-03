from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

PartitionGranularity = Literal["month"]


@dataclass(slots=True)
class StagingStoragePolicy:
    retention_days: int = 90
    partition_granularity: PartitionGranularity = "month"
    partition_prefix: str = "raw_ingestion_events"

    def retention_cutoff(self, reference_time: datetime | None = None) -> datetime:
        now = _normalize_reference_time(reference_time)
        return now - timedelta(days=self.retention_days)

    def is_expired(
        self,
        received_at: datetime,
        reference_time: datetime | None = None,
    ) -> bool:
        return received_at < self.retention_cutoff(reference_time)

    def partition_key(self, received_at: datetime) -> str:
        timestamp = _normalize_reference_time(received_at)
        if self.partition_granularity == "month":
            return timestamp.strftime("%Y_%m")
        raise ValueError(
            f"unsupported partition granularity: {self.partition_granularity}"
        )

    def partition_table_name(self, received_at: datetime) -> str:
        return f"{self.partition_prefix}_{self.partition_key(received_at)}"


def _normalize_reference_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
