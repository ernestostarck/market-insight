"""Unit tests for app.monitoring package modules (alerts, logging, request_id)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.monitoring.alerts import (
    AlertSeverity,
    OperationalAlert,
    dispatch_alert,
)
from app.monitoring.logging import JSONFormatter, get_logger
from app.monitoring.request_id import get_request_id, reset_request_id, set_request_id


def test_operational_alert_format():
    """Verify alert payload serialization adheres to Alertmanager v2 schema."""
    alert = OperationalAlert(
        name="ETLWorkerStalled",
        summary="ETL worker pipeline has stalled",
        severity=AlertSeverity.CRITICAL,
        description="No job heartbeats received in the last 15 minutes.",
        team="data-engineering",
        labels={"pipeline": "chilecompra_tenders"},
        annotations={"runbook": "https://wiki.internal/runbooks/etl"},
    )

    data = alert.to_alertmanager_dict()
    assert data["labels"]["alertname"] == "ETLWorkerStalled"
    assert data["labels"]["severity"] == "critical"
    assert data["labels"]["team"] == "data-engineering"
    assert data["labels"]["pipeline"] == "chilecompra_tenders"
    assert data["annotations"]["summary"] == "ETL worker pipeline has stalled"
    assert "startsAt" in data


@pytest.mark.asyncio
async def test_dispatch_alert_success():
    """Verify dispatch_alert sends payload to Alertmanager."""
    alert = OperationalAlert(
        name="HighMemoryUsage",
        summary="Container memory above 90%",
        severity=AlertSeverity.WARNING,
        description="cAdvisor reports memory exceeded 90% threshold.",
    )

    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        success = await dispatch_alert(alert, alertmanager_url="http://mock-alertmanager:9093")
        assert success is True
        mock_post.assert_called_once()


def test_request_id_context_lifecycle():
    """Verify set_request_id, get_request_id, and reset_request_id work correctly."""
    token = set_request_id("test-req-id-12345")
    try:
        assert get_request_id() == "test-req-id-12345"
    finally:
        reset_request_id(token)


def test_logging_module_reexports():
    """Verify logging module exports valid logger and JSONFormatter."""
    logger = get_logger("test.monitoring")
    assert logger.name == "test.monitoring"

    formatter = JSONFormatter()
    assert formatter is not None
