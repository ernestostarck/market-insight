from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.client_ip import client_ip
from app.core.security import decode_access_token
from app.core.settings import get_settings
from app.schemas.errors import ErrorDetail, ErrorResponse

_EXEMPT_PATHS = {
    "/",
    "/api/v1/",
    "/api/v1/health",
    "/api/v1/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window request throttling backed by Redis, shared across instances.

    Fails open (lets the request through) if Redis is unreachable, so an
    infrastructure outage never takes down the API on its own.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        settings = get_settings()
        self._enabled = settings.rate_limit_enabled
        self._limit = settings.rate_limit_requests
        self._window_seconds = settings.rate_limit_window_seconds
        self._redis: redis.Redis | None = (
            redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            if self._enabled
            else None
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self._enabled or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        identity = _client_identity(request)
        window = int(time.time()) // self._window_seconds
        key = f"rate_limit:{identity}:{window}"

        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, self._window_seconds)
        except Exception:
            return await call_next(request)

        if count > self._limit:
            retry_after = self._window_seconds - (int(time.time()) % self._window_seconds)
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="RATE_LIMIT_EXCEEDED",
                        message="Too many requests. Please try again later.",
                        request_id=getattr(request.state, "request_id", None),
                    )
                ).model_dump(),
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self._limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(max(self._limit - count, 0))
        return response


def _client_identity(request: Request) -> str:
    """Rate-limit authenticated users by identity, anonymous callers by IP.

    Keying authenticated traffic by user (not IP) keeps one busy user from
    throttling everyone else behind the same NAT/proxy.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        subject = decode_access_token(auth_header[7:])
        if subject:
            return f"user:{subject}"
    return f"ip:{client_ip(request)}"
