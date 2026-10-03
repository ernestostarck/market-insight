from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    """Detailed health and latency status of an internal or external component."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Operational status of the component."
    )
    message: str | None = Field(
        default=None, description="Descriptive status message or error details."
    )
    latency_ms: float | None = Field(
        default=None, description="Round-trip latency in milliseconds, if applicable."
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Additional component-specific diagnostic metadata."
    )


class ETLStatusSummary(BaseModel):
    """High-level summary of ETL pipeline freshness and last execution."""

    status: Literal["healthy", "degraded", "stale", "failed"] = Field(
        ..., description="Current status of the ETL pipelines."
    )
    last_run_timestamp: str | None = Field(
        default=None, description="ISO timestamp of last successful ETL sync."
    )
    data_freshness_seconds: float | None = Field(
        default=None, description="Seconds elapsed since last processed tender publication."
    )


class DataQualityStatusSummary(BaseModel):
    """Current consolidated Data Quality indicator."""

    score: float = Field(
        ..., ge=0.0, le=100.0, description="Consolidated Data Quality Score (0 to 100)."
    )
    status: Literal["healthy", "degraded", "critical"] = Field(
        ..., description="Evaluation status based on quality score threshold."
    )
    last_evaluated: str | None = Field(
        default=None, description="Timestamp of latest quality batch evaluation."
    )


class LayerAvailability(BaseModel):
    """Availability of one layer, with the concrete reasons behind a non-healthy status."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Availability of this layer."
    )
    reasons: list[str] = Field(
        default_factory=list, description="Why the layer is not healthy (empty when healthy)."
    )


class AvailabilitySummary(BaseModel):
    """Technical availability and data availability, assessed independently.

    A platform can be technically up while its data is stale (ingestion stopped),
    and data can be fresh while a dependency is down. They are never conflated,
    and neither is inferred from business volume (e.g. fewer tenders published).
    """

    technical: LayerAvailability = Field(
        ..., description="Can the platform serve requests? API, PostgreSQL, Redis, storage, upstream reachability."
    )
    data: LayerAvailability = Field(
        ..., description="Is the data current and trustworthy? Freshness and quality score."
    )


class SystemStatusResponse(BaseModel):
    """Comprehensive global system status and operational observability response (Fase 8.14)."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Global consolidated health status of the platform."
    )
    timestamp: datetime = Field(
        ..., description="UTC timestamp of the status evaluation."
    )
    app_name: str = Field(..., description="Application name.")
    version: str = Field(..., description="Deployed semantic release version.")
    environment: str = Field(..., description="Execution environment.")
    components: dict[str, ComponentHealth] = Field(
        ..., description="Individual health checks for system dependencies."
    )
    etl: ETLStatusSummary = Field(
        ..., description="ETL synchronization and data freshness status."
    )
    data_quality: DataQualityStatusSummary = Field(
        ..., description="Data quality metrics and compliance score."
    )
    availability: AvailabilitySummary = Field(
        ..., description="Technical availability and data availability, assessed separately."
    )
