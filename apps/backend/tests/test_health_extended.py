from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps.settings import get_settings
from app.main import app
from app.schemas.health import DependencyDetail


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides.clear()
    settings = get_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_top_level_health_liveness(client: TestClient) -> None:
    """Subphase 8.1.1 & 8.1.2: Root /health and /health/live."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "MercadoInsight API"
    assert "uptime_seconds" in data
    assert "timestamp" in data

    resp_live = client.get("/health/live")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["status"] == "ok"
    assert data_live["uptime_seconds"] >= 0


def test_api_v1_health_liveness(client: TestClient) -> None:
    """Subphase 8.1.2: /api/v1/health/live."""
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_health_readiness_all_healthy(client: TestClient) -> None:
    """Subphase 8.1.3 to 8.1.7: Readiness returns 200 OK when core dependencies are healthy."""
    with patch(
        "app.monitoring.health.HealthChecker.check_postgres",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.2)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_redis",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=0.8)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_storage",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=2.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_workers",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.5)),
    ):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["postgres"]["status"] == "healthy"
        assert data["dependencies"]["postgres"]["latency_ms"] == 1.2
        assert data["dependencies"]["redis"]["status"] == "healthy"
        assert data["dependencies"]["storage"]["status"] == "healthy"
        assert data["dependencies"]["workers"]["status"] == "healthy"

        # Also test /api/v1/health/ready
        v1_resp = client.get("/api/v1/health/ready")
        assert v1_resp.status_code == 200
        assert v1_resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_health_readiness_postgres_failure(client: TestClient) -> None:
    """Subphase 8.1.4: Readiness returns 503 Service Unavailable when Postgres fails."""
    with patch(
        "app.monitoring.health.HealthChecker.check_postgres",
        new=AsyncMock(
            return_value=DependencyDetail(
                status="unhealthy", latency_ms=15.0, error="Connection refused"
            )
        ),
    ), patch(
        "app.monitoring.health.HealthChecker.check_redis",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=0.5)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_storage",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_workers",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["postgres"]["status"] == "unhealthy"
        assert data["dependencies"]["postgres"]["error"] == "Connection refused"
        assert data["dependencies"]["redis"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_readiness_redis_failure(client: TestClient) -> None:
    """Subphase 8.1.5: Readiness returns 503 Service Unavailable when Redis fails."""
    with patch(
        "app.monitoring.health.HealthChecker.check_postgres",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_redis",
        new=AsyncMock(
            return_value=DependencyDetail(
                status="unhealthy", latency_ms=10.0, error="Redis timeout"
            )
        ),
    ), patch(
        "app.monitoring.health.HealthChecker.check_storage",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_workers",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["redis"]["status"] == "unhealthy"
        assert data["dependencies"]["redis"]["error"] == "Redis timeout"


@pytest.mark.asyncio
async def test_health_readiness_with_external_probe(client: TestClient) -> None:
    """Subphase 8.1.6: Readiness check with optional include_external=true."""
    with patch(
        "app.monitoring.health.HealthChecker.check_postgres",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_redis",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=0.5)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_storage",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.2)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_workers",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=1.0)),
    ), patch(
        "app.monitoring.health.HealthChecker.check_chilecompra",
        new=AsyncMock(return_value=DependencyDetail(status="healthy", latency_ms=45.0)),
    ):
        resp = client.get("/api/v1/health/ready?include_external=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "chilecompra" in data["dependencies"]
        assert data["dependencies"]["chilecompra"]["status"] == "healthy"


def test_prometheus_metrics_endpoint(client: TestClient) -> None:
    """Subphase 8.2: Verify Prometheus metrics endpoint, requests count, duration and buckets."""
    # Send test requests to generate telemetry
    client.get("/api/v1/health")
    client.get("/non-existent-endpoint-for-metrics-test-404")

    # Fetch /metrics
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.text

    # Verify requests total
    assert "http_requests_total" in body

    # Verify duration histogram & P95/P99 calibrated buckets
    assert "http_request_duration_seconds_bucket" in body
    assert 'le="0.5"' in body
    assert 'le="1.0"' in body
    assert 'le="10.0"' in body

    # Verify error metrics counter
    assert "http_errors_total" in body
