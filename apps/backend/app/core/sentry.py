"""Sentry error tracking integration and sensitive data sanitizer (Fase 8.12).

Provides environment-aware exception tracking, stacktrace capturing,
request correlation, and rigorous PII/secret scrubbing.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.context import get_request_id
from app.core.logging import redact_value
from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = frozenset({
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "chilecompra_api_key",
    "chilecompra_api_ticket",
    "authorization",
    "cookie",
    "secret_key",
    "private_key",
})


def _is_sensitive_key(key: Any) -> bool:
    clean = str(key).lower().replace("-", "_")
    return clean in _SENSITIVE_KEYS or any(
        term in clean
        for term in (
            "password",
            "secret",
            "token",
            "api_key",
            "ticket",
            "authorization",
            "cookie",
        )
    )


def _sanitize_dict(data: Any) -> Any:
    """Recursively scrub sensitive keys and values from dictionaries/lists."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            if _is_sensitive_key(k):
                cleaned[k] = "***REDACTED***"
            else:
                cleaned[k] = _sanitize_dict(v)
        return cleaned
    if isinstance(data, (list, tuple)):
        return [_sanitize_dict(item) for item in data]
    return data


def filter_sentry_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Scrub sensitive information and enrich with correlation tags before sending."""
    # 1. Inject correlation tags
    tags = event.setdefault("tags", {})
    req_id = get_request_id()
    if req_id and req_id != "-":
        tags["request_id"] = req_id
    tags["service"] = "market-insight-backend"

    # 2. Scrub request data and headers
    if "request" in event and isinstance(event["request"], dict):
        req = event["request"]
        if "headers" in req and isinstance(req["headers"], dict):
            req["headers"] = _sanitize_dict(req["headers"])
        if "data" in req:
            req["data"] = _sanitize_dict(req["data"])
        if "query_string" in req and isinstance(req["query_string"], dict):
            req["query_string"] = _sanitize_dict(req["query_string"])

    # 3. Scrub extra metadata
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = _sanitize_dict(event["extra"])

    # 4. Deep pass over everything else: messages, exception values, breadcrumbs and the
    # local variables captured in stack frames all carry free text that can hold a secret.
    return redact_value(event)  # type: ignore[return-value]


def setup_sentry(settings: Settings | None = None) -> bool:
    """Initialize Sentry SDK if SENTRY_DSN is provided."""
    current_settings = settings or get_settings()
    dsn = current_settings.sentry_dsn

    if not dsn or not dsn.strip():
        logger.info("Sentry DSN not configured; error tracking disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        env = current_settings.sentry_environment or current_settings.environment
        release = f"{current_settings.app_name}@{current_settings.app_version}"

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            release=release,
            traces_sample_rate=current_settings.sentry_traces_sample_rate,
            profiles_sample_rate=current_settings.sentry_profiles_sample_rate,
            send_default_pii=False,
            before_send=filter_sentry_event,
            before_send_transaction=filter_sentry_event,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        logger.info("Sentry initialized successfully for environment '%s'.", env)
        return True
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to initialize Sentry: %s", err)
        return False
