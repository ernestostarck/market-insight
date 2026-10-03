from __future__ import annotations

from app.core.sentry import filter_sentry_event, setup_sentry
from app.core.settings import Settings
from app.core.telemetry import get_current_trace_id, setup_telemetry


def test_sentry_event_filter_scrubs_sensitive_data() -> None:
    raw_event = {
        "tags": {},
        "request": {
            "headers": {
                "authorization": "Bearer secret_jwt_token",
                "x-api-key": "secret_key_123",
                "content-type": "application/json",
            },
            "data": {
                "username": "admin@example.com",
                "password": "MySuperSecretPassword",
                "chilecompra_api_ticket": "top_secret_ticket",
            },
        },
        "extra": {
            "token": "sensitive_refresh_token",
            "normal_field": "visible_value",
        },
    }

    filtered = filter_sentry_event(raw_event, {})
    assert filtered is not None

    headers = filtered["request"]["headers"]
    assert headers["authorization"] == "***REDACTED***"
    assert headers["x-api-key"] == "***REDACTED***"
    assert headers["content-type"] == "application/json"

    data = filtered["request"]["data"]
    assert data["password"] == "***REDACTED***"
    assert data["chilecompra_api_ticket"] == "***REDACTED***"
    assert data["username"] == "admin@example.com"

    extra = filtered["extra"]
    assert extra["token"] == "***REDACTED***"
    assert extra["normal_field"] == "visible_value"


def test_setup_sentry_without_dsn() -> None:
    settings = Settings(sentry_dsn=None)
    assert setup_sentry(settings) is False


def test_setup_telemetry_disabled() -> None:
    settings = Settings(otel_enabled=False)
    assert setup_telemetry(settings=settings) is False


def test_setup_telemetry_enabled() -> None:
    settings = Settings(otel_enabled=True, otel_service_name="test-service")
    assert setup_telemetry(settings=settings) is True
    # Verify trace function does not crash
    trace_id = get_current_trace_id()
    assert trace_id is None or isinstance(trace_id, str)
