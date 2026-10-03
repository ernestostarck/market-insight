"""Tests for AI SQLAlchemy models (Conversation and Message in schema 'ai') (Fase 9.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.ai import Conversation, Message


def test_conversation_model_schema_and_tablename() -> None:
    assert Conversation.__tablename__ == "conversation"
    # Verify table schema is 'ai'
    table_args = Conversation.__table_args__
    schema_found = False
    for arg in table_args:
        if isinstance(arg, dict) and arg.get("schema") == "ai":
            schema_found = True
            break
    assert schema_found is True, "Conversation model must be in PostgreSQL schema 'ai'"


def test_message_model_schema_and_tablename() -> None:
    assert Message.__tablename__ == "message"
    table_args = Message.__table_args__
    schema_found = False
    for arg in table_args:
        if isinstance(arg, dict) and arg.get("schema") == "ai":
            schema_found = True
            break
    assert schema_found is True, "Message model must be in PostgreSQL schema 'ai'"


def test_conversation_instantiation_and_defaults() -> None:
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    conv = Conversation(
        id=conv_id,
        user_id=user_id,
        title="Gasto en Obras Públicas",
        status="active",
        metadata_={"department": "Analítica", "tags": ["mop", "infraestructura"]},
    )
    assert conv.id == conv_id
    assert conv.user_id == user_id
    assert conv.title == "Gasto en Obras Públicas"
    assert conv.status == "active"
    assert conv.metadata_["department"] == "Analítica"
    assert len(conv.messages) == 0


def test_message_instantiation_and_roles() -> None:
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.now(UTC)

    roles = ["system", "user", "assistant", "tool"]
    for role in roles:
        msg = Message(
            id=msg_id,
            conversation_id=conv_id,
            role=role,
            content=f"Mensaje con rol {role}",
            model="gemini-2.5-flash" if role == "assistant" else None,
            tokens_input=150 if role == "assistant" else None,
            tokens_output=80 if role == "assistant" else None,
            latency_ms=345.2 if role == "assistant" else None,
            metadata_={"test": True},
            created_at=now,
        )
        assert msg.role == role
        assert msg.conversation_id == conv_id
        if role == "assistant":
            assert msg.tokens_input == 150
            assert msg.tokens_output == 80
            assert msg.latency_ms == 345.2
            assert msg.model == "gemini-2.5-flash"


def test_conversation_message_relationship() -> None:
    conv = Conversation(
        id=uuid.uuid4(),
        title="Sesión de prueba",
        status="active",
        metadata_={},
    )
    msg1 = Message(
        id=uuid.uuid4(),
        role="user",
        content="Hola, ¿cuántas licitaciones hay activas hoy?",
    )
    msg2 = Message(
        id=uuid.uuid4(),
        role="assistant",
        content="Hoy hay 1.420 licitaciones publicadas en Mercado Público.",
        model="gpt-4o",
        tokens_input=45,
        tokens_output=18,
        latency_ms=210.5,
    )

    conv.messages.append(msg1)
    conv.messages.append(msg2)

    assert len(conv.messages) == 2
    assert conv.messages[0].content == "Hola, ¿cuántas licitaciones hay activas hoy?"
    assert conv.messages[1].model == "gpt-4o"
    assert msg1.conversation == conv
    assert msg2.conversation == conv
