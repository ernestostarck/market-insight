from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    get_route_path,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect basic Prometheus metrics for each request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Observability security: protect /metrics if METRICS_AUTH_TOKEN is configured
        if request.url.path == "/metrics":
            from app.api.deps.settings import get_settings

            settings = get_settings()
            if settings.metrics_auth_token:
                auth_header = request.headers.get("Authorization", "")
                token_header = request.headers.get("X-Metrics-Token", "")
                provided_token = None
                if auth_header.startswith("Bearer "):
                    provided_token = auth_header[7:].strip()
                elif token_header:
                    provided_token = token_header.strip()

                if not provided_token or provided_token != settings.metrics_auth_token:
                    return Response(
                        content="Unauthorized: Valid metrics token required\n",
                        status_code=401,
                        media_type="text/plain",
                    )

        start_time = time.perf_counter()
        response = await call_next(request)
        path = get_route_path(request)
        status_code = str(response.status_code)
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_TOTAL.labels(request.method, path, status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(request.method, path, status_code).observe(
            duration
        )
        return response
