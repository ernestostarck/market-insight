"""Alertmanager webhook receiver (Fase 8.10).

Alertmanager posts grouped notifications here over the internal network. Each
alert becomes one structured log line, so it lands in Loki next to the service
logs, and increments a counter that shows notification delivery end to end.
"""

from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps.settings import Settings, get_settings
from app.monitoring.metrics import ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL

router = APIRouter()
logger = logging.getLogger("app.alerts")

_LOG_LEVELS = {"critical": logging.ERROR, "warning": logging.WARNING}


class WebhookAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "firing"
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None


class AlertmanagerWebhook(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "firing"
    receiver: str | None = None
    alerts: list[WebhookAlert] = Field(default_factory=list)


def _authorize(settings: Settings, authorization: str | None) -> None:
    """Fail closed: only development/test may run without a shared token."""
    token = settings.alert_webhook_token
    if not token:
        if settings.environment in ("development", "test"):
            return
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Alert webhook is not configured")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), token.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid alert webhook token")


@router.post(
    "/alerts/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def receive_alertmanager_webhook(
    payload: AlertmanagerWebhook,
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _authorize(settings, authorization)

    for alert in payload.alerts:
        alertname = alert.labels.get("alertname", "unknown")
        severity = alert.labels.get("severity", "unknown")
        ALERTMANAGER_NOTIFICATIONS_RECEIVED_TOTAL.labels(
            alertname=alertname, severity=severity, status=alert.status
        ).inc()
        logger.log(
            _LOG_LEVELS.get(severity, logging.INFO) if alert.status == "firing" else logging.INFO,
            "ALERT %s %s [%s] %s",
            alert.status.upper(),
            alertname,
            severity,
            alert.annotations.get("summary", ""),
            extra={
                "event": "alert_notification",
                "alert_name": alertname,
                "alert_status": alert.status,
                "severity": severity,
                "receiver": payload.receiver,
                "summary": alert.annotations.get("summary"),
                "description": alert.annotations.get("description"),
                "alert_labels": alert.labels,
            },
        )
    return {"received": len(payload.alerts)}
