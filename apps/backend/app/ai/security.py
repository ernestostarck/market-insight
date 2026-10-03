"""AI Security, PII Minimization and Access Control Layer (Fase 9.25).

Provides:
1. PII Sanitization (Redaction of credit cards, personal emails, personal phones)
2. Strict conversation ownership & authorization enforcement
3. Structured security audit logging
4. Context minimization (No sending superfluous or internal system data to external LLMs)
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

logger = logging.getLogger("ai.security.audit")

# Regex patterns for sensitive PII
_CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
_EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_REGEX = re.compile(r"(?:\+?56\s?9\s?\d{4}\s?\d{4}|\b9\d{8}\b)")


class PIISanitizer:
    """Detects and redacts sensitive personal data before external LLM calls."""

    @classmethod
    def sanitize(cls, text: str) -> tuple[str, list[str]]:
        """Mask credit card numbers, personal emails and phone numbers.

        Returns a tuple of (sanitized_text, list_of_detected_pii_categories).
        """
        if not text:
            return text, []

        detected: list[str] = []
        sanitized = text

        if _CREDIT_CARD_REGEX.search(sanitized):
            detected.append("credit_card")
            sanitized = _CREDIT_CARD_REGEX.sub("[TARJETA_PROTEGIDA]", sanitized)

        if _EMAIL_REGEX.search(sanitized):
            detected.append("email")
            sanitized = _EMAIL_REGEX.sub("[EMAIL_PROTEGIDO]", sanitized)

        if _PHONE_REGEX.search(sanitized):
            detected.append("phone")
            sanitized = _PHONE_REGEX.sub("[TELEFONO_PROTEGIDO]", sanitized)

        return sanitized, detected


class ConversationAccessController:
    """Enforces strict user isolation across conversations."""

    @staticmethod
    def verify_ownership(
        conversation_user_id: UUID | None,
        requesting_user_id: UUID | None,
    ) -> None:
        """Verify that the requesting user owns the conversation.

        Raises 404 (Not Found) rather than 403 to avoid leaking conversation existence.
        """
        if conversation_user_id is None:
            # System-level or unassigned conversation
            return

        if requesting_user_id is None or conversation_user_id != requesting_user_id:
            logger.warning(
                "Unauthorized conversation access attempt: owner=%s, requester=%s",
                conversation_user_id,
                requesting_user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o acceso denegado.",
            )


class SecurityAuditLogger:
    """Emits structured audit logs for AI interactions and security incidents."""

    @staticmethod
    def log_event(
        event_type: str,
        user_id: UUID | None,
        conversation_id: UUID | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a structured security audit record."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "audit_event": event_type,
            "user_id": str(user_id) if user_id else "anonymous",
            "conversation_id": str(conversation_id) if conversation_id else "none",
            "details": details or {},
        }
        logger.info("AUDIT_LOG: %s", record)
