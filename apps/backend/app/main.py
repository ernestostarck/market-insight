import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

if sys.platform == "win32":
    with contextlib.suppress(Exception):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps.settings import Settings, get_settings
from app.api.v1.router import api_router as v1_router
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics_middleware import MetricsMiddleware
from app.core.firewall import FirewallMiddleware, SecurityHeadersMiddleware
from app.core.middleware import RequestIDMiddleware
from app.core.openapi import TAGS_METADATA
from app.core.rate_limit import RateLimitMiddleware
from app.core.sentry import setup_sentry
from app.core.telemetry import setup_telemetry
from app.monitoring.data_freshness import run_freshness_refresher
from app.monitoring.health import HealthChecker, run_chilecompra_probe
from app.monitoring.metrics import setup_metrics

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle events."""
    configure_logging()
    setup_sentry(settings)
    setup_telemetry(app, settings)
    logging.getLogger(__name__).info(
        "Starting %s v%s in %s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    background = [
        asyncio.create_task(run_freshness_refresher()),
        asyncio.create_task(run_chilecompra_probe(settings)),
    ]
    try:
        yield
    finally:
        for task in background:
            task.cancel()
        for task in background:
            with contextlib.suppress(asyncio.CancelledError):
                await task
    logging.getLogger(__name__).info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create the FastAPI application with middleware, routes and handlers."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Plataforma de inteligencia de mercado para ChileCompra y Mercado Publico.",
        description=(
            "Captura, normaliza, enriquece, analiza y expone licitaciones, contratos, ordenes "
            "de compra, proveedores y organismos publicados a traves de ChileCompra.\n\n"
            "### Autenticacion\n"
            "La mayoria de los endpoints requieren un bearer token JWT. Obtenlo con "
            "`POST /api/v1/auth/login` (OAuth2 password flow: `username` es el email) y envialo "
            "como `Authorization: Bearer <token>`. Usa el boton **Authorize** de esta pagina para "
            "probarlo interactivamente.\n\n"
            "### Paginacion\n"
            "Los listados usan paginacion por cursor (keyset): pasa el `next_cursor`/`prev_cursor` "
            "de la respuesta anterior en el parametro `cursor` para navegar.\n\n"
            "### Rate limiting\n"
            "Las respuestas incluyen `X-RateLimit-Limit`/`X-RateLimit-Remaining`. Al exceder el "
            "limite se devuelve `429` con un header `Retry-After` en segundos."
        ),
        openapi_tags=TAGS_METADATA,
        # The interactive docs map the whole attack surface: only exposed in development.
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
        max_age=600,
    )
    # Added last = runs first: the firewall rejects hostile traffic before any other work,
    # and every response (including firewall rejections) carries the security headers.
    app.add_middleware(FirewallMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    # Subphase 8.2: Initialize Prometheus FastAPI Instrumentator
    setup_metrics(app)

    # Subphase 8.1: Top-level Health Probes (for Docker/Kubernetes orchestrators)
    @app.get(
        "/health",
        tags=["health"],
        summary="Health check",
        include_in_schema=False,
    )
    async def root_health(settings: Settings = Depends(get_settings)):
        checker = HealthChecker(settings)
        return await checker.check_liveness()

    @app.get(
        "/health/live",
        tags=["health"],
        summary="Liveness check",
        include_in_schema=False,
    )
    async def root_liveness(settings: Settings = Depends(get_settings)):
        checker = HealthChecker(settings)
        return await checker.check_liveness()

    @app.get(
        "/health/ready",
        tags=["health"],
        summary="Readiness check",
        include_in_schema=False,
    )
    async def root_readiness(settings: Settings = Depends(get_settings)):
        checker = HealthChecker(settings)
        readiness_data, is_ready = await checker.check_readiness()
        status_code = 200 if is_ready else 503
        return JSONResponse(status_code=status_code, content=readiness_data.model_dump())

    @app.get(
        "/system/status",
        tags=["health"],
        summary="System status alias",
        include_in_schema=False,
    )
    async def root_system_status(settings: Settings = Depends(get_settings)):
        from app.api.v1.endpoints.system import get_system_status

        return await get_system_status(settings)

    @app.get(
        "/",
        tags=["metadata"],
        summary="Service info",
        description="Top-level service metadata and links to docs/health, outside the "
        "versioned API prefix.",
    )
    def root(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
