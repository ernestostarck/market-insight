from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse

from app.api.deps.settings import Settings, get_settings
from app.api.deps.use_cases import SystemStatusUseCase, get_system_status_use_case
from app.monitoring.health import HealthChecker
from app.schemas.health import (
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check general",
    description="Reports service name, version, and environment. Backward compatible.",
)
def health_check(
    settings: Settings = Depends(get_settings),
    use_case: SystemStatusUseCase = Depends(get_system_status_use_case),
) -> HealthResponse:
    system_status = use_case.execute(settings)
    return HealthResponse.model_validate(system_status)


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    tags=["health"],
    summary="Liveness check",
    description="Checks if the FastAPI server process is running and responding without checking external dependencies.",
)
async def liveness_check(
    settings: Settings = Depends(get_settings),
) -> LivenessResponse:
    checker = HealthChecker(settings)
    return await checker.check_liveness()


@router.get(
    "/live",
    response_model=LivenessResponse,
    tags=["health"],
    summary="Liveness probe alias",
    include_in_schema=False,
)
async def liveness_alias(
    settings: Settings = Depends(get_settings),
) -> LivenessResponse:
    return await liveness_check(settings)


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "All core dependencies (PostgreSQL, Redis) are healthy."},
        503: {"description": "One or more critical dependencies are down."},
    },
    tags=["health"],
    summary="Readiness check",
    description="Probes availability of PostgreSQL, Redis, Storage and Workers. Returns 200 OK or 503 Service Unavailable.",
)
async def readiness_check(
    include_external: bool = Query(
        default=False, description="Whether to include external ChileCompra API probe."
    ),
    settings: Settings = Depends(get_settings),
) -> Response:
    checker = HealthChecker(settings)
    readiness_data, is_ready = await checker.check_readiness(
        include_external=include_external
    )
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=readiness_data.model_dump())


@router.get(
    "/ready",
    tags=["health"],
    summary="Readiness probe alias",
    include_in_schema=False,
)
async def readiness_alias(
    settings: Settings = Depends(get_settings),
) -> Response:
    return await readiness_check(include_external=False, settings=settings)


@router.get(
    "/",
    tags=["metadata"],
    summary="API root",
    description="Basic service metadata under the versioned API prefix.",
)
def api_root(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
