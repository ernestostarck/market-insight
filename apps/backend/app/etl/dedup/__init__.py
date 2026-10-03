from app.etl.dedup.engine import DeduplicationEngine
from app.etl.dedup.models import (
    DedupDecision,
    DedupPolicy,
    DedupResult,
)
from app.etl.dedup.repository import (
    DedupRepository,
    ExistingRecord,
    InMemoryDedupRepository,
    SqlAlchemyDedupRepository,
)
from app.etl.dedup.service import partition_by_action, summarize_result

__all__ = [
    "DeduplicationEngine",
    "DedupDecision",
    "DedupPolicy",
    "DedupResult",
    "DedupRepository",
    "ExistingRecord",
    "InMemoryDedupRepository",
    "SqlAlchemyDedupRepository",
    "partition_by_action",
    "summarize_result",
]
