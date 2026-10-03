"""System status and operational observability endpoints (Fase 8.14).

Provides /api/v1/system/status exposing consolidated platform health,
component latencies (PostgreSQL, Redis, MinIO, ChileCompra), ETL freshness,
and data quality indicators.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps.settings import Settings, get_settings
from app.monitoring.data_freshness import FreshnessState, refresh_data_freshness
from app.monitoring.health import HealthChecker, get_uptime_seconds
from app.monitoring.metrics import DATA_QUALITY_SCORE
from app.schemas.system import (
    AvailabilitySummary,
    ComponentHealth,
    DataQualityStatusSummary,
    ETLStatusSummary,
    LayerAvailability,
    SystemStatusResponse,
)

router = APIRouter()


def _get_metric_gauge_value(gauge_metric: Any, **labels: str) -> float | None:
    """Current value of a Prometheus Gauge, or None if it was never observed.

    Calling ``.labels()`` on an unobserved series would create it at 0.0, which
    reads as a real measurement (e.g. a data quality score of 0), so the child is
    looked up without being created.
    """
    try:
        label_names = getattr(gauge_metric, "_labelnames", ())
        if label_names:
            child = gauge_metric._metrics.get(tuple(labels[name] for name in label_names))
            return float(child._value.get()) if child is not None else None
        return float(gauge_metric._value.get())
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Global system operational status",
    description="Returns consolidated health status of all internal and external components, ETL freshness and Data Quality.",
)
async def get_system_status(
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    checker = HealthChecker(settings)

    # 1. Run component probes concurrently
    postgres_dep, redis_dep, minio_dep, chilecompra_dep = await asyncio.gather(
        checker.check_postgres(timeout=2.0),
        checker.check_redis(timeout=2.0),
        checker.check_storage(timeout=2.0),
        checker.check_chilecompra(timeout=3.0),
    )

    components: dict[str, ComponentHealth] = {
        "api": ComponentHealth(
            status="healthy",
            message=f"FastAPI process running (uptime {get_uptime_seconds()}s)",
            latency_ms=0.5,
            details={"uptime_seconds": get_uptime_seconds()},
        ),
        "postgres": ComponentHealth(
            status="healthy" if postgres_dep.status == "healthy" else "unhealthy",
            message=postgres_dep.error or "PostgreSQL connection pool healthy",
            latency_ms=postgres_dep.latency_ms,
        ),
        "redis": ComponentHealth(
            status="healthy" if redis_dep.status == "healthy" else "unhealthy",
            message=redis_dep.error or "Redis cache and broker responding",
            latency_ms=redis_dep.latency_ms,
        ),
        "minio": ComponentHealth(
            status="healthy" if minio_dep.status == "healthy" else "degraded",
            message=minio_dep.error or "Object storage S3/MinIO reachable",
            latency_ms=minio_dep.latency_ms,
        ),
        "chilecompra": ComponentHealth(
            status="healthy" if chilecompra_dep.status == "healthy" else "degraded",
            message=chilecompra_dep.error or "MercadoPublico public API responding",
            latency_ms=chilecompra_dep.latency_ms,
        ),
    }

    # 2. Extract ETL sync and data freshness metrics via data freshness service
    freshness_report = await refresh_data_freshness(pipeline="chilecompra_tenders")
    last_run_iso = freshness_report.last_processed_timestamp
    freshness_seconds = freshness_report.freshness_seconds

    etl_status_str = "healthy"
    if freshness_report.status == FreshnessState.CRITICAL:
        etl_status_str = "stale"
    elif freshness_report.status == FreshnessState.WARNING:
        etl_status_str = "degraded"
    else:
        etl_status_str = "healthy"

    etl_summary = ETLStatusSummary(
        status=etl_status_str,
        last_run_timestamp=last_run_iso,
        data_freshness_seconds=freshness_seconds,
    )

    # 3. Extract Data Quality score
    quality_score = _get_metric_gauge_value(
        DATA_QUALITY_SCORE, pipeline="chilecompra_tenders"
    )
    if quality_score is None:
        quality_score = 100.0

    if quality_score >= 95.0:
        quality_status_str = "healthy"
    elif quality_score >= 85.0:
        quality_status_str = "degraded"
    else:
        quality_status_str = "critical"

    data_quality_summary = DataQualityStatusSummary(
        score=quality_score,
        status=quality_status_str,
        last_evaluated=datetime.now(UTC).isoformat(),
    )

    # 4. Technical and data availability, assessed independently. Volume of
    # tenders is deliberately not an input: fewer publications is not an outage.
    technical_reasons = [
        f"{name}: {c.message}" for name, c in components.items() if c.status != "healthy"
    ]
    technical_status = (
        "unhealthy"
        if any(c.status == "unhealthy" for c in components.values())
        else "degraded"
        if technical_reasons
        else "healthy"
    )

    data_reasons: list[str] = []
    if freshness_report.status != FreshnessState.NORMAL:
        upstream = (
            "ChileCompra is reachable, so look at the ETL pipeline"
            if components["chilecompra"].status == "healthy"
            else "ChileCompra is unreachable, so the upstream may be the cause"
        )
        data_reasons.append(f"freshness {freshness_report.status.value}: {upstream}")
    if quality_status_str != "healthy":
        data_reasons.append(f"data quality {quality_status_str}: score {quality_score}")
    data_status = (
        "unhealthy"
        if freshness_report.status == FreshnessState.CRITICAL or quality_status_str == "critical"
        else "degraded"
        if data_reasons
        else "healthy"
    )

    availability = AvailabilitySummary(
        technical=LayerAvailability(status=technical_status, reasons=technical_reasons),
        data=LayerAvailability(status=data_status, reasons=data_reasons),
    )

    # 5. Synthesize consolidated global status
    has_critical = any(c.status == "unhealthy" for c in components.values())
    has_degraded = (
        any(c.status == "degraded" for c in components.values())
        or etl_status_str == "stale"
        or quality_status_str in ("degraded", "critical")
    )

    if has_critical:
        global_status = "unhealthy"
    elif has_degraded:
        global_status = "degraded"
    else:
        global_status = "healthy"

    return SystemStatusResponse(
        status=global_status,
        timestamp=datetime.now(UTC),
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        components=components,
        etl=etl_summary,
        data_quality=data_quality_summary,
        availability=availability,
    )
