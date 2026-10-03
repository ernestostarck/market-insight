from typing import Protocol

from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord


class RecordLoader(Protocol):
    def load(
        self,
        run: IngestionRunContext,
        records: list[TransformedRecord],
    ) -> LoadResult: ...
