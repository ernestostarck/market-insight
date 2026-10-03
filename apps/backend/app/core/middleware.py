from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

import sentry_sdk
from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.context import reset_request_id, set_request_id

access_logger = logging.getLogger("app.access")

# A client-supplied X-Request-ID ends up in logs, Sentry tags, spans and the
# response header, so anything that isn't a plain token (newlines, spaces,
# oversized values) is discarded and replaced with a server-generated UUID.
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


def resolve_request_id(candidate: str | None) -> str:
    if candidate and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def _tag_current_span(request_id: str) -> None:
    """Attach the request ID to the active server span so a trace can be found from a log line.

    The OTel server span starts before this middleware runs (and before the ID exists
    when the client did not send one), so it is tagged here rather than in the span hook.
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("app.request_id", request_id)
        span.set_attribute("correlation_id", request_id)


def _tag_error_tracking(request_id: str) -> None:
    """Tag the request's Sentry scope. Unhandled exceptions are captured by Sentry's ASGI
    layer *after* this middleware has unwound and reset the context variable, so reading the
    ID at send time would find it empty."""
    sentry_sdk.get_isolation_scope().set_tag("request_id", request_id)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request identifier to every response and log line, and emit a
    structured access log entry per request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = resolve_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = set_request_id(request_id)
        _tag_current_span(request_id)
        _tag_error_tracking(request_id)
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"

            access_logger.info(
                "%s %s %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": request.client.host if request.client else None,
                },
            )
            return response
        finally:
            reset_request_id(token)
