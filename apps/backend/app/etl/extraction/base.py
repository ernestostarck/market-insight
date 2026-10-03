from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.etl.models import IngestionRunContext, RawRecord


@dataclass(slots=True)
class ExtractionWindow:
    start_at: datetime | None = None
    end_at: datetime | None = None


@dataclass(slots=True)
class ExtractionCursor:
    marker: str
    updated_at: datetime


class DataSource(Protocol):
    """Contract for external data extractors (API, open data, files)."""

    source_name: str

    async def extract(
        self,
        run: IngestionRunContext,
        window: ExtractionWindow | None = None,
    ) -> list[RawRecord]: ...
