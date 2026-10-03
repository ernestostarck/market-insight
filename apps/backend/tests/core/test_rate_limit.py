from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware
from app.core.security import create_access_token


class _FakeRedis:
    """In-memory stand-in for the async Redis client's incr/expire calls."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


class _RaisingRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis unreachable")

    async def expire(self, key: str, seconds: int) -> None:
        raise ConnectionError("redis unreachable")


async def _ok(request):
    return PlainTextResponse("ok")


def _build_client(*, enabled: bool, limit: int = 3, window: int = 60, redis=None) -> TestClient:
    inner = Starlette(routes=[Route("/test", _ok), Route("/api/v1/health", _ok)])
    middleware = RateLimitMiddleware(inner)
    middleware._enabled = enabled
    middleware._limit = limit
    middleware._window_seconds = window
    middleware._redis = redis if redis is not None else _FakeRedis()
    return TestClient(middleware)


def test_exempt_path_bypasses_rate_limiting_entirely() -> None:
    client = _build_client(enabled=True, limit=1)

    for _ in range(5):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "x-ratelimit-limit" not in response.headers


def test_requests_under_limit_pass_with_headers() -> None:
    client = _build_client(enabled=True, limit=3)

    response = client.get("/test")

    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"] == "3"
    assert response.headers["x-ratelimit-remaining"] == "2"


def test_requests_exceeding_limit_return_429_with_retry_after() -> None:
    client = _build_client(enabled=True, limit=2)

    assert client.get("/test").status_code == 200
    assert client.get("/test").status_code == 200
    blocked = client.get("/test")

    assert blocked.status_code == 429
    assert blocked.headers["x-ratelimit-remaining"] == "0"
    assert "retry-after" in blocked.headers
    assert int(blocked.headers["retry-after"]) >= 0
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_disabled_middleware_never_throttles() -> None:
    client = _build_client(enabled=False, limit=1)

    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200
        assert "x-ratelimit-limit" not in response.headers


def test_fails_open_when_redis_is_unreachable() -> None:
    client = _build_client(enabled=True, limit=1, redis=_RaisingRedis())

    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200


def test_different_bearer_tokens_get_independent_limits() -> None:
    client = _build_client(enabled=True, limit=1)
    token_a = create_access_token(subject="user_a@example.com")
    token_b = create_access_token(subject="user_b@example.com")

    first_a = client.get("/test", headers={"Authorization": f"Bearer {token_a}"})
    first_b = client.get("/test", headers={"Authorization": f"Bearer {token_b}"})
    second_a = client.get("/test", headers={"Authorization": f"Bearer {token_a}"})

    assert first_a.status_code == 200
    assert first_b.status_code == 200
    assert second_a.status_code == 429


def test_anonymous_requests_are_limited_by_ip() -> None:
    client = _build_client(enabled=True, limit=1)

    first = client.get("/test")
    second = client.get("/test")

    assert first.status_code == 200
    assert second.status_code == 429
