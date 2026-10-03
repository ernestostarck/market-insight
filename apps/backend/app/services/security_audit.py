"""Write security events to the append-only `security.audit_log`.

Events are written in their own session/transaction so they are kept even when the
request that triggered them fails (e.g. a rejected login), and a logging failure never
breaks the request itself.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from starlette.requests import HTTPConnection

from app.core.client_ip import client_ip
from app.db.session import AsyncSessionLocal
from app.models.user import SecurityAuditLog

logger = logging.getLogger("app.security.audit")

# Event names (kept stable: dashboards and alerts key on them).
LOGIN_SUCCESS = "login_success"
LOGIN_FAILED = "login_failed"
LOGIN_BLOCKED_LOCKED = "login_blocked_locked"
ACCOUNT_LOCKED = "account_locked"
MFA_CHALLENGE_FAILED = "mfa_challenge_failed"
MFA_ENABLED = "mfa_enabled"
MFA_DISABLED = "mfa_disabled"
TOKEN_REFRESHED = "token_refreshed"
REFRESH_TOKEN_REUSE = "refresh_token_reuse_detected"
LOGOUT = "logout"
LOGOUT_ALL = "logout_all"
SESSION_REVOKED = "session_revoked"
PASSWORD_CHANGED = "password_changed"
PASSWORD_CHANGE_FAILED = "password_change_failed"
PROFILE_UPDATED = "profile_updated"
USER_CREATED = "user_created"
USER_UPDATED = "user_updated"
FIREWALL_BLOCK = "firewall_block"
IP_BANNED = "ip_banned"
AUTH_RATE_LIMITED = "auth_rate_limited"


async def record(
    event: str,
    *,
    request: HTTPConnection | None = None,
    user_id: uuid.UUID | None = None,
    email: str | None = None,
    success: bool = True,
    detail: dict[str, Any] | None = None,
) -> None:
    entry = SecurityAuditLog(
        event=event,
        success=success,
        user_id=user_id,
        actor_email=email,
        ip_address=client_ip(request) if request is not None else None,
        user_agent=(request.headers.get("user-agent") or "")[:400] if request is not None else None,
        request_id=getattr(request.state, "request_id", None) if request is not None else None,
        detail=detail or {},
    )
    log_extra = {"security_event": event, "success": success, "actor": email}
    try:
        async with AsyncSessionLocal() as session:
            session.add(entry)
            await session.commit()
    except Exception:  # pragma: no cover - audit must never take the request down
        logger.exception("Could not persist security audit event %s", event, extra=log_extra)
        return
    logger.info("security event %s", event, extra=log_extra)
