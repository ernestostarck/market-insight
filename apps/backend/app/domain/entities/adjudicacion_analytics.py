from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class AdjudicacionAnalyticsSnapshotRecord:
    id: int | None
    external_id: str
    snapshot_date: date
    scored_at: datetime
    opportunity_score: float
    risk_level: str
    is_outlier: bool
    reasons: list[str]
    award_ratio: float | None = None
    awarded_amount: float | None = None
    quality_flags: list[str] | None = None
    source_filters: dict[str, str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
