from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.chilecompra.models import AdjudicacionesScoringConfig


class PersistAdjudicacionesByDateRequest(BaseModel):
    fecha: str = Field(..., description="Date to fetch adjudicaciones for, as DDMMYYYY (ChileCompra format).")
    config: AdjudicacionesScoringConfig | None = Field(
        None, description="Optional overrides for the opportunity/risk scoring thresholds."
    )


class PersistAdjudicacionesByQueryRequest(BaseModel):
    query: dict[str, str | int | float] = Field(
        ..., description="Arbitrary ChileCompra advanced-search query parameters."
    )
    snapshot_date: date = Field(..., description="Date to stamp the resulting snapshots with.")
    config: AdjudicacionesScoringConfig | None = Field(
        None, description="Optional overrides for the opportunity/risk scoring thresholds."
    )


class AdjudicacionAnalyticsSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal snapshot identifier.")
    external_id: str = Field(..., description="ChileCompra adjudicacion identifier.")
    snapshot_date: date = Field(..., description="Date this snapshot represents.")
    scored_at: datetime = Field(..., description="Timestamp when scoring was computed.")
    opportunity_score: float = Field(..., description="Computed opportunity score (higher is better).")
    risk_level: str = Field(..., description="Risk bucket: low, medium or high.")
    is_outlier: bool = Field(..., description="Whether this award was flagged as a statistical outlier.")
    reasons: list[str] = Field(..., description="Human-readable reasons behind the score.")
    award_ratio: float | None = Field(None, description="Awarded amount over estimated amount.")
    awarded_amount: float | None = Field(None, description="Amount awarded, in CLP.")
    quality_flags: list[str] = Field(
        default_factory=list, description="Data-quality issues detected in the source payload."
    )
    source_filters: dict[str, str] = Field(
        default_factory=dict, description="Filters used to fetch the source data for this snapshot."
    )
    is_degraded_source: bool = Field(
        False, description="Whether this snapshot fell back to a degraded/incomplete data source."
    )
    source_resource: str | None = Field(None, description="Which ChileCompra resource the data came from.")


class AdjudicacionesPersistenceSummaryResponse(BaseModel):
    persisted_items: int = Field(..., description="Number of snapshots written.")
    outlier_items: int = Field(..., description="Of those, how many were flagged as outliers.")
    avg_opportunity_score: float | None = Field(None, description="Average opportunity score across persisted items.")
    risk_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of persisted items per risk_level."
    )


class AdjudicacionesTimeseriesPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date = Field(..., description="Day this point summarizes.")
    total_items: int = Field(..., description="Total snapshots on this day.")
    outlier_items: int = Field(..., description="Snapshots flagged as outliers on this day.")
    degraded_items: int = Field(..., description="Snapshots from a degraded data source on this day.")
    degraded_ratio: float = Field(..., description="degraded_items / total_items for this day.")
    avg_opportunity_score: float | None = Field(None, description="Average opportunity score on this day.")
    risk_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of snapshots per risk_level on this day."
    )


class AdjudicacionDashboardRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_id: str = Field(..., description="ChileCompra adjudicacion identifier.")
    snapshot_date: date = Field(..., description="Date this record represents.")
    opportunity_score: float = Field(..., description="Computed opportunity score.")
    risk_level: str = Field(..., description="Risk bucket: low, medium or high.")
    is_outlier: bool = Field(..., description="Whether this award was flagged as a statistical outlier.")
    is_degraded_source: bool = Field(..., description="Whether the source data was degraded/incomplete.")
    awarded_amount: float | None = Field(None, description="Amount awarded, in CLP.")
    award_ratio: float | None = Field(None, description="Awarded amount over estimated amount.")
    reasons: list[str] = Field(default_factory=list, description="Human-readable reasons behind the score.")
    quality_flags: list[str] = Field(default_factory=list, description="Data-quality issues detected.")


class AdjudicacionesDashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_date: date = Field(..., description="Start of the summarized date range.")
    end_date: date = Field(..., description="End of the summarized date range.")
    total_items: int = Field(..., description="Total snapshots in range after filters.")
    unique_external_ids: int = Field(..., description="Distinct adjudicaciones represented in range.")
    outlier_items: int = Field(..., description="Snapshots flagged as outliers.")
    degraded_items: int = Field(..., description="Snapshots from a degraded data source.")
    outlier_ratio: float = Field(..., description="outlier_items / total_items.")
    degraded_ratio: float = Field(..., description="degraded_items / total_items.")
    avg_opportunity_score: float | None = Field(None, description="Average opportunity score in range.")
    risk_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of snapshots per risk_level."
    )
    applied_filters: dict[str, str | bool | int | float] = Field(
        default_factory=dict, description="Echo of the filters/pagination that produced this summary."
    )
    source_breakdown: list["AdjudicacionesDashboardBreakdownResponse"] = Field(
        default_factory=list, description="Metrics grouped by source resource, one page per breakdown params."
    )
    source_breakdown_pagination: "AdjudicacionesDashboardBreakdownPaginationResponse" = Field(
        ..., description="Pagination info for source_breakdown."
    )
    organization_breakdown: list["AdjudicacionesDashboardBreakdownResponse"] = Field(
        default_factory=list, description="Metrics grouped by buying organism, one page per breakdown params."
    )
    organization_breakdown_pagination: "AdjudicacionesDashboardBreakdownPaginationResponse" = Field(
        ..., description="Pagination info for organization_breakdown."
    )
    top_risk_items: list[AdjudicacionDashboardRecordResponse] = Field(
        default_factory=list, description="Highest-risk items in range, up to `limit`."
    )
    top_opportunity_items: list[AdjudicacionDashboardRecordResponse] = Field(
        default_factory=list, description="Highest-opportunity items in range, up to `limit`."
    )


class AdjudicacionesDashboardBreakdownResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment: str = Field(..., description="Group label (source resource name or organism id).")
    total_items: int = Field(..., description="Snapshots in this segment.")
    outlier_items: int = Field(..., description="Outlier snapshots in this segment.")
    degraded_items: int = Field(..., description="Degraded-source snapshots in this segment.")
    outlier_ratio: float = Field(..., description="outlier_items / total_items for this segment.")
    degraded_ratio: float = Field(..., description="degraded_items / total_items for this segment.")
    avg_opportunity_score: float | None = Field(None, description="Average opportunity score in this segment.")
    risk_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of snapshots per risk_level in this segment."
    )


class AdjudicacionesDashboardBreakdownPaginationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int = Field(..., description="Current page number, 1-indexed.")
    page_size: int = Field(..., description="Segments per page.")
    total_items: int = Field(..., description="Total segments across all pages.")
    total_pages: int = Field(..., description="Total number of pages.")
    has_next: bool = Field(..., description="Whether a next page exists.")
    has_prev: bool = Field(..., description="Whether a previous page exists.")
    next_page: int | None = Field(None, description="Next page number, if any.")
    prev_page: int | None = Field(None, description="Previous page number, if any.")
    sort_by: str = Field(..., description="Metric the breakdown was sorted by.")
    sort_desc: bool = Field(..., description="Whether the sort order was descending.")
