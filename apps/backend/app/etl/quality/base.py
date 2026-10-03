from typing import Protocol

from app.etl.models import ETLMetrics, IngestionRunContext


class QualityReporter(Protocol):
    def emit(self, run: IngestionRunContext, metrics: ETLMetrics) -> None: ...
