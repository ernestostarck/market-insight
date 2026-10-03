from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RawIngestionEventRecord:
    id: int | None
    ingestion_run_id: str
    source: str
    resource: str
    source_id: str
    payload: dict[str, Any]
    payload_hash: str
    metadata: dict[str, str] | None = None
    received_at: datetime | None = None
    created_at: datetime | None = None
