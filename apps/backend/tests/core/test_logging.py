from __future__ import annotations

import json
import logging

from app.core import logging as app_logging
from app.core.context import reset_request_id, set_request_id
from app.core.logging import (
    ConsoleFormatter,
    ContextFilter,
    JSONFormatter,
    _resolve_format,
    build_logging_config,
)
from app.core.settings import Settings


def _make_record(**overrides) -> logging.LogRecord:
    record = logging.LogRecord(
        name=overrides.pop("name", "app.test"),
        level=overrides.pop("level", logging.INFO),
        pathname=__file__,
        lineno=1,
        msg=overrides.pop("msg", "hello"),
        args=overrides.pop("args", ()),
        exc_info=overrides.pop("exc_info", None),
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


def test_resolve_format_auto_uses_console_in_development() -> None:
    assert _resolve_format("auto", "development") == "console"


def test_resolve_format_auto_uses_json_outside_development() -> None:
    assert _resolve_format("auto", "staging") == "json"
    assert _resolve_format("auto", "production") == "json"


def test_resolve_format_explicit_value_ignores_environment() -> None:
    assert _resolve_format("json", "development") == "json"
    assert _resolve_format("console", "production") == "console"


def test_context_filter_injects_app_and_request_context() -> None:
    record = _make_record()
    token = set_request_id("req-123")
    try:
        result = ContextFilter().filter(record)
    finally:
        reset_request_id(token)

    assert result is True
    assert record.request_id == "req-123"
    assert record.app_name
    assert record.environment


def test_context_filter_defaults_request_id_when_outside_a_request() -> None:
    record = _make_record()

    ContextFilter().filter(record)

    assert record.request_id == "-"


def test_json_formatter_produces_parseable_line_with_expected_fields() -> None:
    record = _make_record(
        msg="something happened",
        app_name="MercadoInsight API",
        environment="development",
        request_id="req-abc",
        user_id=42,
    )

    line = JSONFormatter().format(record)
    payload = json.loads(line)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "something happened"
    assert payload["app_name"] == "MercadoInsight API"
    assert payload["environment"] == "development"
    assert payload["request_id"] == "req-abc"
    assert payload["user_id"] == 42


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _make_record(msg="failed", exc_info=sys.exc_info())

    payload = json.loads(JSONFormatter().format(record))

    assert "ValueError: boom" in payload["exception"]


def test_console_formatter_includes_request_id_and_message() -> None:
    record = _make_record(msg="hello world", request_id="req-xyz")

    line = ConsoleFormatter().format(record)

    assert "rid=req-xyz" in line
    assert "hello world" in line
    assert "INFO" in line


def test_build_logging_config_uses_info_for_sqlalchemy_when_log_sql_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        app_logging,
        "get_settings",
        lambda: Settings(_env_file=None, LOG_SQL="true", ENVIRONMENT="development"),
    )

    config = build_logging_config()

    assert config["loggers"]["sqlalchemy.engine"]["level"] == "INFO"


def test_build_logging_config_uses_warning_for_sqlalchemy_by_default(monkeypatch) -> None:
    monkeypatch.setattr(
        app_logging,
        "get_settings",
        lambda: Settings(_env_file=None, LOG_SQL="false", ENVIRONMENT="development"),
    )

    config = build_logging_config()

    assert config["loggers"]["sqlalchemy.engine"]["level"] == "WARNING"


def test_build_logging_config_selects_console_formatter_in_development(monkeypatch) -> None:
    monkeypatch.setattr(
        app_logging,
        "get_settings",
        lambda: Settings(_env_file=None, ENVIRONMENT="development", LOG_FORMAT="auto"),
    )

    config = build_logging_config()

    assert config["handlers"]["default"]["formatter"] == "console"


def test_build_logging_config_selects_json_formatter_in_production(monkeypatch) -> None:
    monkeypatch.setattr(
        app_logging,
        "get_settings",
        lambda: Settings(_env_file=None, ENVIRONMENT="production", SECRET_KEY="a-real-secret-with-at-least-32-characters", LOG_FORMAT="auto"),
    )

    config = build_logging_config()

    assert config["handlers"]["default"]["formatter"] == "json"
