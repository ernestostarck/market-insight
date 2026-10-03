from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(slots=True)
class ExtractionCheckpoint:
    source: str
    resource: str
    marker: str
    updated_at: datetime


class CheckpointStore(Protocol):
    def get(self, *, source: str, resource: str) -> ExtractionCheckpoint | None: ...

    def set(self, checkpoint: ExtractionCheckpoint) -> None: ...


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], ExtractionCheckpoint] = {}

    def get(self, *, source: str, resource: str) -> ExtractionCheckpoint | None:
        return self._items.get((source, resource))

    def set(self, checkpoint: ExtractionCheckpoint) -> None:
        self._items[(checkpoint.source, checkpoint.resource)] = checkpoint


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
