from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request

HTTP_REQUESTS_TOTAL = Counter(
    "market_insight_http_requests_total",
    "Total HTTP requests processed by the API.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "market_insight_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


def get_route_path(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
