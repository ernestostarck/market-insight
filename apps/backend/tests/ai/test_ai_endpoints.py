"""Unit tests for AI Conversational REST API endpoints (Fase 9.2 & 9.3).

Tests /api/v1/ai/conversations routes:
1. POST /api/v1/ai/conversations
2. GET  /api/v1/ai/conversations/{id}
3. POST /api/v1/ai/conversations/{id}/messages
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai.contracts import (
    ChatMessage,
    ConversationSession,
    ConversationStatus,
    MessageRole,
)
from app.ai.session_service import (
    SessionAuthorizationError,
    SessionConcurrencyError,
    SessionService,
    get_session_service,
)
from app.db.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "analyst@marketinsight.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_session_service() -> MagicMock:
    service = MagicMock(spec=SessionService)
    return service


@pytest.fixture
def client(mock_user: User) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. POST /ai/conversations
# ---------------------------------------------------------------------------


def test_create_conversation_endpoint(client: TestClient, mock_user: User) -> None:
    conv_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service = MagicMock(spec=SessionService)
    mock_service.aget_or_create_session = AsyncMock(
        return_value=ConversationSession(
            id=conv_id,
            user_id=mock_user.id,
            title="Análisis de Proveedores TI",
            status=ConversationStatus.ACTIVE,
            metadata={"source": "api_test"},
            created_at=now,
            updated_at=now,
        )
    )
    app.dependency_overrides[get_session_service] = lambda: mock_service

    payload = {
        "title": "Análisis de Proveedores TI",
        "metadata": {"source": "api_test"},
    }
    response = client.post("/api/v1/ai/conversations", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(conv_id)
    assert data["user_id"] == str(mock_user.id)
    assert data["title"] == "Análisis de Proveedores TI"
    assert data["status"] == "active"
    assert data["metadata"] == {"source": "api_test"}


# ---------------------------------------------------------------------------
# 2. GET /ai/conversations/{id}
# ---------------------------------------------------------------------------


def test_get_conversation_endpoint_success(client: TestClient, mock_user: User) -> None:
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service = MagicMock(spec=SessionService)
    mock_service.aget_or_create_session = AsyncMock(
        return_value=ConversationSession(
            id=conv_id,
            user_id=mock_user.id,
            title="Detalle Conversación",
            status=ConversationStatus.ACTIVE,
            metadata={},
            created_at=now,
            updated_at=now,
        )
    )
    mock_service.get_messages = MagicMock(
        return_value=[
            ChatMessage(
                id=msg_id,
                conversation_id=conv_id,
                role=MessageRole.USER,
                content="¿Cuál es el mayor proveedor de salud?",
                created_at=now,
            )
        ]
    )
    app.dependency_overrides[get_session_service] = lambda: mock_service

    # Mock run_sync to execute sync function
    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=lambda fn: fn(MagicMock()))
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get(f"/api/v1/ai/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation"]["id"] == str(conv_id)
    assert len(data["messages"]) == 1
    assert data["messages"][0]["id"] == str(msg_id)
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "¿Cuál es el mayor proveedor de salud?"


def test_get_conversation_endpoint_unauthorized(client: TestClient) -> None:
    conv_id = uuid.uuid4()

    mock_service = MagicMock(spec=SessionService)
    mock_service.aget_or_create_session = AsyncMock(
        side_effect=SessionAuthorizationError("No autorizado para ver esta conversación.")
    )
    app.dependency_overrides[get_session_service] = lambda: mock_service

    response = client.get(f"/api/v1/ai/conversations/{conv_id}")

    assert response.status_code == 403
    assert "No autorizado" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. POST /ai/conversations/{id}/messages
# ---------------------------------------------------------------------------


def test_add_message_endpoint_success(client: TestClient, mock_user: User) -> None:
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_service = MagicMock(spec=SessionService)

    @asynccontextmanager
    async def _mock_lock(_id: uuid.UUID) -> AsyncIterator[str]:
        yield "token-123"

    mock_service.acquire_conversation_lock = _mock_lock
    mock_service.save_message = MagicMock(
        return_value=ChatMessage(
            id=msg_id,
            conversation_id=conv_id,
            role=MessageRole.USER,
            content="Dame el resumen del último mes.",
            created_at=now,
        )
    )
    app.dependency_overrides[get_session_service] = lambda: mock_service

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=lambda fn: fn(MagicMock()))
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "role": "user",
        "content": "Dame el resumen del último mes.",
    }
    response = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(msg_id)
    assert data["conversation_id"] == str(conv_id)
    assert data["role"] == "user"
    assert data["content"] == "Dame el resumen del último mes."


def test_add_message_endpoint_invalid_role(client: TestClient) -> None:
    conv_id = uuid.uuid4()
    payload = {
        "role": "unknown_role",
        "content": "Mensaje inválido",
    }
    response = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json=payload)
    assert response.status_code == 400
    assert "no es válido" in response.json()["detail"]


def test_add_message_endpoint_concurrency_conflict(client: TestClient) -> None:
    conv_id = uuid.uuid4()

    mock_service = MagicMock(spec=SessionService)

    @asynccontextmanager
    async def _locked_out(_id: uuid.UUID) -> AsyncIterator[str]:
        raise SessionConcurrencyError("Conversación bloqueada por proceso concurrente.")
        yield ""  # pragma: no cover

    mock_service.acquire_conversation_lock = _locked_out
    app.dependency_overrides[get_session_service] = lambda: mock_service

    payload = {
        "role": "user",
        "content": "Mensaje simultáneo",
    }
    response = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json=payload)
    assert response.status_code == 409
    assert "bloqueada" in response.json()["detail"]


def test_add_message_endpoint_unauthorized(client: TestClient) -> None:
    conv_id = uuid.uuid4()

    mock_service = MagicMock(spec=SessionService)

    @asynccontextmanager
    async def _mock_lock(_id: uuid.UUID) -> AsyncIterator[str]:
        yield "token-123"

    mock_service.acquire_conversation_lock = _mock_lock
    mock_service.save_message = MagicMock(
        side_effect=SessionAuthorizationError("Usuario no autorizado para esta conversación.")
    )
    app.dependency_overrides[get_session_service] = lambda: mock_service

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=lambda fn: fn(MagicMock()))
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "role": "user",
        "content": "Intento no autorizado",
    }
    response = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json=payload)
    assert response.status_code == 403
    assert "no autorizado" in response.json()["detail"]
