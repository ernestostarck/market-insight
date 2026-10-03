"""Unit and integration tests for Observability Security and /metrics protection."""

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.api.deps.settings import Settings
from app.core.metrics_middleware import MetricsMiddleware


@pytest.fixture
def base_app() -> FastAPI:
    """Create a test application equipped with MetricsMiddleware."""
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics")
    def metrics_endpoint():
        return PlainTextResponse("mock_metrics_data\n")

    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}

    return app


def test_metrics_open_by_default(base_app, monkeypatch):
    """When METRICS_AUTH_TOKEN is not configured, /metrics is accessible."""
    mock_settings = Settings(METRICS_AUTH_TOKEN=None)
    monkeypatch.setattr("app.api.deps.settings.get_settings", lambda: mock_settings)

    client = TestClient(base_app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "mock_metrics_data" in response.text


def test_metrics_blocked_without_token_when_configured(base_app, monkeypatch):
    """When METRICS_AUTH_TOKEN is configured, /metrics rejects unauthenticated requests with 401."""
    secret_token = "ultra-secure-metrics-secret-key-123"
    mock_settings = Settings(METRICS_AUTH_TOKEN=secret_token)
    monkeypatch.setattr("app.api.deps.settings.get_settings", lambda: mock_settings)

    client = TestClient(base_app)

    # 1. No auth headers provided
    response = client.get("/metrics")
    assert response.status_code == 401
    assert "Unauthorized" in response.text

    # 2. Invalid Bearer token
    response_bad = client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})
    assert response_bad.status_code == 401

    # 3. Invalid X-Metrics-Token header
    response_bad_header = client.get("/metrics", headers={"X-Metrics-Token": "bad-key"})
    assert response_bad_header.status_code == 401


def test_metrics_allowed_with_valid_token(base_app, monkeypatch):
    """When METRICS_AUTH_TOKEN is configured, /metrics accepts valid Bearer or header tokens."""
    secret_token = "ultra-secure-metrics-secret-key-123"
    mock_settings = Settings(METRICS_AUTH_TOKEN=secret_token)
    monkeypatch.setattr("app.api.deps.settings.get_settings", lambda: mock_settings)

    client = TestClient(base_app)

    # 1. Valid Bearer token
    res_bearer = client.get("/metrics", headers={"Authorization": f"Bearer {secret_token}"})
    assert res_bearer.status_code == 200
    assert "mock_metrics_data" in res_bearer.text

    # 2. Valid X-Metrics-Token header
    res_header = client.get("/metrics", headers={"X-Metrics-Token": secret_token})
    assert res_header.status_code == 200
    assert "mock_metrics_data" in res_header.text


def test_regular_endpoints_unaffected_by_metrics_auth(base_app, monkeypatch):
    """Endpoints other than /metrics (e.g. /health) should not be blocked by metrics auth."""
    mock_settings = Settings(METRICS_AUTH_TOKEN="strictly-protected-token")
    monkeypatch.setattr("app.api.deps.settings.get_settings", lambda: mock_settings)

    client = TestClient(base_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
