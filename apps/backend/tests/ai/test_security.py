"""Unit tests for AI Security and PII minimization (Fase 9.25)."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.ai.security import (
    ConversationAccessController,
    PIISanitizer,
    SecurityAuditLogger,
)


def test_pii_sanitizer_credit_cards():
    query_cc = "Pago realizado con tarjeta 4532-1234-5678-9010 para compra de insumos."
    clean, detected = PIISanitizer.sanitize(query_cc)
    assert "credit_card" in detected
    assert "4532-1234-5678-9010" not in clean
    assert "[TARJETA_PROTEGIDA]" in clean


def test_pii_sanitizer_emails_and_phones():
    query_contact = "Contactar a juan.perez@empresa.cl o al celular +56 9 8765 4321 para la cotización."
    clean, detected = PIISanitizer.sanitize(query_contact)
    assert "email" in detected
    assert "phone" in detected
    assert "juan.perez@empresa.cl" not in clean
    assert "[EMAIL_PROTEGIDO]" in clean
    assert "[TELEFONO_PROTEGIDO]" in clean


def test_pii_sanitizer_clean_text_unchanged():
    query_clean = "Licitaciones de sillas de ruedas en Municipalidad de Las Condes en 2024."
    clean, detected = PIISanitizer.sanitize(query_clean)
    assert detected == []
    assert clean == query_clean


def test_conversation_access_controller_ownership():
    owner = uuid4()
    intruder = uuid4()

    # Allowed for owner
    ConversationAccessController.verify_ownership(owner, owner)

    # Allowed for unassigned conversation
    ConversationAccessController.verify_ownership(None, intruder)

    # Rejection for intruder (raises 404 to avoid leaking existence)
    with pytest.raises(HTTPException) as exc_info:
        ConversationAccessController.verify_ownership(owner, intruder)
    assert exc_info.value.status_code == 404


def test_security_audit_logger_emits_log():
    # Should execute cleanly without errors
    SecurityAuditLogger.log_event(
        event_type="test_probe",
        user_id=uuid4(),
        conversation_id=uuid4(),
        details={"status": "ok"},
    )
