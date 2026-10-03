from __future__ import annotations

import json
import logging

from app.core.logging import JSONFormatter


def test_json_formatter_standard_fields() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-12345"
    record.service = "market-insight-backend"
    record.pipeline = "chilecompra_tenders"
    record.event = "tender_fetch_completed"
    record.run_id = "run-999"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["message"] == "Test message"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["request_id"] == "req-12345"
    assert parsed["service"] == "market-insight-backend"
    assert parsed["pipeline"] == "chilecompra_tenders"
    assert parsed["event"] == "tender_fetch_completed"
    assert parsed["run_id"] == "run-999"
    assert "timestamp" in parsed


def test_json_formatter_error_handling() -> None:
    formatter = JSONFormatter()
    try:
        raise ValueError("Simulated failure")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=25,
        msg="An error occurred",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "ERROR"
    assert "ValueError: Simulated failure" in parsed["error"]


def test_json_formatter_sensitive_data_redaction() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=35,
        msg="User authenticated",
        args=(),
        exc_info=None,
    )
    record.password = "SuperSecretPassword123"
    record.api_key = "secret_api_key_xyz"
    record.chilecompra_api_key = "chilecompra_ticket_secret"

    output = formatter.format(record)
    parsed = json.loads(output)

    # Values must be redacted
    assert "SuperSecretPassword123" not in output
    assert parsed["extra"]["password"] == "Su***23"
    assert parsed["extra"]["api_key"] == "se***yz"
    assert parsed["extra"]["chilecompra_api_key"] == "ch***et"
