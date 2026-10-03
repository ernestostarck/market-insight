"""Operational Alerting module for MercadoInsight (Fase 8).

Implements principles of non-spurious alerting:
- Does not generate alerts solely because a business indicator changed.
- Differentiates normal market cycles (weekends, holidays) from operational failures.
- Keeps secrets out of alert payloads and notifications.
- Optionally dispatches alerts to Prometheus Alertmanager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

from app.core.logging import redact_text

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Severity levels for operational alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(slots=True)
class OperationalAlert:
    """Structured representation of an operational alert."""

    name: str
    summary: str
    severity: AlertSeverity
    description: str
    team: str = "platform"
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_alertmanager_dict(self) -> dict[str, Any]:
        """Format alert payload compatible with Alertmanager v2 API."""
        # Alerts fan out to email/Slack/webhooks: nothing secret may ride along.
        return {
            "labels": {
                "alertname": self.name,
                "severity": self.severity.value,
                "team": self.team,
                **{k: redact_text(v) for k, v in self.labels.items()},
            },
            "annotations": {
                "summary": redact_text(self.summary),
                "description": redact_text(self.description),
                **{k: redact_text(v) for k, v in self.annotations.items()},
            },
            "startsAt": self.timestamp.isoformat(),
        }


async def dispatch_alert(
    alert: OperationalAlert,
    alertmanager_url: str = "http://alertmanager:9093",
    timeout: float = 3.0,
) -> bool:
    """Log structured alert and dispatch to Alertmanager API v2."""
    logger.warning(
        "OPERATIONAL_ALERT: [%s] %s - %s",
        alert.severity.value.upper(),
        alert.name,
        alert.summary,
        extra={
            "alert_name": alert.name,
            "severity": alert.severity.value,
            "summary": alert.summary,
            "description": alert.description,
            "team": alert.team,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{alertmanager_url}/api/v2/alerts",
                json=[alert.to_alertmanager_dict()],
            )
            return resp.status_code in (200, 202)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not dispatch alert to Alertmanager at %s: %s", alertmanager_url, exc)
        return False
