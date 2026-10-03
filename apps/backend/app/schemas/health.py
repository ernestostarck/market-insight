from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DependencyHealthStatus = Literal["healthy", "unhealthy", "degraded"]


class DependencyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: DependencyHealthStatus = Field(
        ..., description="Dependency status: healthy, unhealthy, or degraded."
    )
    latency_ms: float | None = Field(
        default=None, description="Roundtrip latency in milliseconds, if applicable."
    )
    error: str | None = Field(
        default=None, description="Error detail if dependency check failed."
    )


class LivenessResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "ok",
                "timestamp": "2026-03-02T18:00:00Z",
                "service": "MercadoInsight API",
                "version": "0.1.0",
                "uptime_seconds": 124.5,
            }
        },
    )

    status: Literal["ok"] = Field(
        default="ok", description="Liveness indicator, ok if process is answering."
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO-8601 UTC timestamp of the check.",
    )
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="Application version.")
    uptime_seconds: float = Field(
        ..., description="Elapsed process uptime in seconds."
    )


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "ready",
                "timestamp": "2026-03-02T18:00:00Z",
                "service": "MercadoInsight API",
                "version": "0.1.0",
                "environment": "development",
                "dependencies": {
                    "postgres": {"status": "healthy", "latency_ms": 1.5},
                    "redis": {"status": "healthy", "latency_ms": 0.8},
                    "storage": {"status": "healthy", "latency_ms": 2.1},
                    "workers": {"status": "healthy", "latency_ms": 3.0},
                },
            }
        },
    )

    status: Literal["ready", "not_ready"] = Field(
        ..., description="Overall readiness: ready to accept traffic or not_ready."
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO-8601 UTC timestamp of the check.",
    )
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="Application version.")
    environment: str = Field(..., description="Deployment environment.")
    dependencies: dict[str, DependencyDetail] = Field(
        default_factory=dict,
        description="Status details for downstream dependencies.",
    )


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "MercadoInsight API",
                "version": "0.1.0",
                "environment": "development",
            }
        },
    )

    status: str = Field(..., description="Always `ok` if the process is up and answering.")
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="Deployed application version.")
    environment: str = Field(..., description="Deployment environment (development/staging/production).")
