"""Unit tests for SessionService (Fase 9.3).

Tests ephemeral Redis caching, distributed concurrency locking, durable PostgreSQL storage,
and user authorization enforcement.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.contracts import ConversationStatus, MessageRole
from app.ai.session_service import (
    SessionAuthorizationError,
    SessionConcurrencyError,
    SessionService,
    get_session_service,
)
from app.models.ai import Conversation, Message

# ---------------------------------------------------------------------------
# 1. Ephemeral Redis Caching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_session_state_stores_only_metadata() -> None:
    mock_redis = AsyncMock()
    service = SessionService(redis_client=mock_redis, session_ttl=3600)

    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created = datetime.now(UTC)

    await service._cache_session_state(
        conversation_id=conv_id,
        user_id=user_id,
        title="Consulta de prueba",
        status="active",
        created_at=created,
    )

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    key = call_args[0][0]
    payload_str = call_args[0][1]
    ex = call_args[1].get("ex")

    assert key == f"ai:session:{conv_id}"
    assert ex == 3600

    payload = json.loads(payload_str)
    assert payload["conversation_id"] == str(conv_id)
    assert payload["user_id"] == str(user_id)
    assert payload["title"] == "Consulta de prueba"
    assert payload["status"] == "active"
    assert "last_activity_at" in payload

    # CRITICAL: Verify NO message text or conversation history is stored in Redis
    assert "messages" not in payload
    assert "history" not in payload
    assert "content" not in payload


@pytest.mark.asyncio
async def test_touch_session_refreshes_ttl() -> None:
    mock_redis = AsyncMock()
    conv_id = uuid.uuid4()
    existing_meta = {
        "conversation_id": str(conv_id),
        "user_id": str(uuid.uuid4()),
        "title": "Title",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "last_activity_at": datetime.now(UTC).isoformat(),
    }
    mock_redis.get.return_value = json.dumps(existing_meta)

    service = SessionService(redis_client=mock_redis, session_ttl=1800)
    await service._touch_session(conv_id)

    mock_redis.get.assert_called_once_with(f"ai:session:{conv_id}")
    mock_redis.set.assert_called_once()
    assert mock_redis.set.call_args[1]["ex"] == 1800


# ---------------------------------------------------------------------------
# 2. Concurrency Control (Distributed Lock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_conversation_lock_success() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True  # Successfully acquired lock
    service = SessionService(redis_client=mock_redis, lock_ttl=15)

    conv_id = uuid.uuid4()
    async with service.acquire_conversation_lock(conv_id, timeout=1.0) as token:
        assert isinstance(token, str)
        assert len(token) > 0
        mock_redis.set.assert_called_once_with(
            f"ai:lock:conversation:{conv_id}",
            token,
            nx=True,
            ex=15,
        )

    # Verify lock release via Lua script
    mock_redis.eval.assert_called_once()
    eval_args = mock_redis.eval.call_args[0]
    assert "redis.call" in eval_args[0]
    assert eval_args[2] == f"ai:lock:conversation:{conv_id}"
    assert eval_args[3] == token


@pytest.mark.asyncio
async def test_acquire_conversation_lock_contention_raises_error() -> None:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = None  # Lock held by someone else
    service = SessionService(redis_client=mock_redis)

    conv_id = uuid.uuid4()
    with pytest.raises(SessionConcurrencyError) as exc_info:
        async with service.acquire_conversation_lock(conv_id, timeout=0.1):
            pass

    assert f"Conversation {conv_id} is currently locked" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Synchronous Session & Authorization Operations
# ---------------------------------------------------------------------------


def test_get_or_create_session_creates_new() -> None:
    service = SessionService()
    mock_db = MagicMock()
    mock_db.scalar.return_value = None  # Not found

    user_id = uuid.uuid4()
    session = service.get_or_create_session(
        db=mock_db,
        user_id=user_id,
        title="Nueva conversación",
    )

    assert session.user_id == user_id
    assert session.title == "Nueva conversación"
    assert session.status == ConversationStatus.ACTIVE
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_get_or_create_session_retrieves_existing_authorized() -> None:
    service = SessionService()
    mock_db = MagicMock()
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    existing = Conversation(
        id=conv_id,
        user_id=user_id,
        title="Sesión Existente",
        status="active",
        metadata_={"foo": "bar"},
    )
    mock_db.scalar.return_value = existing

    session = service.get_or_create_session(
        db=mock_db,
        conversation_id=conv_id,
        user_id=user_id,
    )

    assert session.id == conv_id
    assert session.user_id == user_id
    assert session.title == "Sesión Existente"
    assert session.metadata == {"foo": "bar"}
    mock_db.add.assert_not_called()


def test_get_or_create_session_unauthorized_raises_error() -> None:
    service = SessionService()
    mock_db = MagicMock()
    conv_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    existing = Conversation(
        id=conv_id,
        user_id=owner_id,
        title="Sesión Privada",
        status="active",
        metadata_={},
    )
    mock_db.scalar.return_value = existing

    with pytest.raises(SessionAuthorizationError) as exc_info:
        service.get_or_create_session(
            db=mock_db,
            conversation_id=conv_id,
            user_id=other_user_id,
        )

    assert "not authorized" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Asynchronous Session Operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aget_or_create_session_async_creates_and_caches() -> None:
    mock_redis = AsyncMock()
    service = SessionService(redis_client=mock_redis)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    user_id = uuid.uuid4()
    session = await service.aget_or_create_session(
        db=mock_db,
        user_id=user_id,
        title="Async Session",
    )

    assert session.user_id == user_id
    assert session.title == "Async Session"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_redis.set.assert_called_once()  # Ephemeral cache


@pytest.mark.asyncio
async def test_aget_or_create_session_unauthorized_raises_error() -> None:
    service = SessionService()
    mock_db = AsyncMock()
    conv_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    intruder_id = uuid.uuid4()

    existing = Conversation(
        id=conv_id,
        user_id=owner_id,
        title="Secret Conversation",
        status="active",
        metadata_={},
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = mock_result

    with pytest.raises(SessionAuthorizationError):
        await service.aget_or_create_session(
            db=mock_db,
            conversation_id=conv_id,
            user_id=intruder_id,
        )


# ---------------------------------------------------------------------------
# 5. Message History Persistence & Authorization
# ---------------------------------------------------------------------------


def test_save_message_success() -> None:
    service = SessionService()
    mock_db = MagicMock()
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    conv = Conversation(id=conv_id, user_id=user_id, status="active", metadata_={})
    mock_db.scalar.return_value = conv

    msg = service.save_message(
        db=mock_db,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="¿Cuál es el presupuesto de la licitación?",
        user_id=user_id,
    )

    assert msg.conversation_id == conv_id
    assert msg.role == MessageRole.USER
    assert msg.content == "¿Cuál es el presupuesto de la licitación?"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_save_message_conversation_not_found_raises_value_error() -> None:
    service = SessionService()
    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    conv_id = uuid.uuid4()

    with pytest.raises(ValueError) as exc_info:
        service.save_message(
            db=mock_db,
            conversation_id=conv_id,
            role=MessageRole.USER,
            content="test",
        )

    assert f"Conversation {conv_id} does not exist" in str(exc_info.value)


def test_save_message_unauthorized_raises_error() -> None:
    service = SessionService()
    mock_db = MagicMock()
    conv_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    conv = Conversation(id=conv_id, user_id=owner_id, status="active", metadata_={})
    mock_db.scalar.return_value = conv

    with pytest.raises(SessionAuthorizationError):
        service.save_message(
            db=mock_db,
            conversation_id=conv_id,
            role=MessageRole.USER,
            content="intento no autorizado",
            user_id=other_user_id,
        )


def test_get_messages_success_and_order() -> None:
    service = SessionService()
    mock_db = MagicMock()
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()

    conv = Conversation(id=conv_id, user_id=user_id, status="active", metadata_={})
    mock_db.scalar.return_value = conv

    m1 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        role="user",
        content="Pregunta 1",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
    )
    m2 = Message(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        role="assistant",
        content="Respuesta 1",
        created_at=datetime(2026, 9, 20, 10, 1, tzinfo=UTC),
    )
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [m1, m2]
    mock_db.scalars.return_value = scalars_mock

    messages = service.get_messages(db=mock_db, conversation_id=conv_id, user_id=user_id)

    assert len(messages) == 2
    assert messages[0].content == "Pregunta 1"
    assert messages[0].role == MessageRole.USER
    assert messages[1].content == "Respuesta 1"
    assert messages[1].role == MessageRole.ASSISTANT


def test_get_session_service_singleton() -> None:
    s1 = get_session_service()
    s2 = get_session_service()
    assert s1 is s2
