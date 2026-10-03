"""Error handling and quarantine layer for the ETL pipeline (Fase 3.12).

The ETL pipeline must never lose original data. Every record that fails
validation or processing is captured in a :class:`QuarantineRecord` and handed
to a :class:`Quarantine` store. The store decides how to persist it (database,
filesystem, dead-letter queue, etc.) while the pipeline stays decoupled from
the concrete backend via the same Protocol-based pattern used elsewhere in the
codebase (``RawIngestor``, ``QualityReporter``).
"""

from __future__ import annotations

from app.etl.error_handling.models import (
    ErrorType,
    QuarantineRecord,
    ValidationFailure,
)
from app.etl.error_handling.quarantine import (
    CompoundQuarantine,
    InMemoryQuarantine,
    LoggingQuarantine,
    Quarantine,
    record_processing_error,
    record_validation_failure,
)

__all__ = [
    "ErrorType",
    "QuarantineRecord",
    "ValidationFailure",
    "Quarantine",
    "InMemoryQuarantine",
    "LoggingQuarantine",
    "CompoundQuarantine",
    "record_validation_failure",
    "record_processing_error",
]
