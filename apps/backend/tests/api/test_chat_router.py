"""Unit and integration tests for Dedicated Chat REST API endpoints (Fase 9.27).

Tests all endpoints under /api/v1/chat:
1. POST   /api/v1/chat
2. POST   /api/v1/chat/stream
3. GET    /api/v1/chat/conversations
4. POST   /api/v1/chat/conversations
5. GET    /api/v1/chat/conversations/{conversation_id}
6. GET    /api/v1/chat/conversations/{conversation_id}/messages
7. PATCH  /api/v1/chat/conversations/{conversation_id}
8. DELETE /api/v1/chat/conversations/{conversation_id}
9. POST   /api/v1/chat/messages/{message_id}/feedback
"""

from __future__ import annotations

import datetime
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai.contracts import ConversationStatus, MessageRole
from app.ai.session_service import SessionAuthorizationError, get_session_service
from app.api.v1.endpoints.chat import get_chat_service
from app.db.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def test_user() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "analyst@marketinsight.com"
    user.is_active = True
    return user


@pytest.fixture
def client(test_user: User) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_list_conversations(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_session = SimpleNamespace(
        id=conv_id,
        user_id=test_user.id,
        title="Licitaciones de Salud 2025",
        status=ConversationStatus.ACTIVE,
        metadata={},
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    mock_svc = MagicMock()
    mock_svc.aget_or_create_session = AsyncMock(return_value=mock_session)
    mock_svc.list_conversations.return_value = [mock_session]
    mock_db.run_sync = AsyncMock(return_value=[mock_session])
    app.dependency_overrides[get_session_service] = lambda: mock_svc

    # 1. POST /api/v1/chat/conversations
    create_resp = client.post(
        "/api/v1/chat/conversations",
        json={"title": "Licitaciones de Salud 2025"},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["id"] == str(conv_id)
    assert data["title"] == "Licitaciones de Salud 2025"

    # 2. GET /api/v1/chat/conversations
    list_resp = client.get("/api/v1/chat/conversations")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == str(conv_id)


def test_get_conversation_detail_and_messages(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)

    mock_session = SimpleNamespace(
        id=conv_id,
        user_id=test_user.id,
        title="Consulta Hospitales",
        status=ConversationStatus.ACTIVE,
        metadata={},
        created_at=now,
        updated_at=now,
    )
    mock_msg = SimpleNamespace(
        id=msg_id,
        conversation_id=conv_id,
        role=MessageRole.USER,
        content="¿Cuánto gastó el Hospital San Juan?",
        model=None,
        tokens_input=None,
        tokens_output=None,
        latency_ms=None,
        metadata={},
        created_at=now,
    )

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(return_value=[mock_msg])
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_svc = MagicMock()
    mock_svc.aget_or_create_session = AsyncMock(return_value=mock_session)
    mock_svc.get_messages.return_value = [mock_msg]
    app.dependency_overrides[get_session_service] = lambda: mock_svc

    # GET /api/v1/chat/conversations/{id}
    resp = client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["conversation"]["id"] == str(conv_id)
    assert len(detail["messages"]) == 1
    assert detail["messages"][0]["content"] == "¿Cuánto gastó el Hospital San Juan?"

    # GET /api/v1/chat/conversations/{id}/messages
    resp_msgs = client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert resp_msgs.status_code == 200
    msgs = resp_msgs.json()
    assert len(msgs) == 1
    assert msgs[0]["id"] == str(msg_id)


def test_rename_and_delete_conversation(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)

    mock_renamed = SimpleNamespace(
        id=conv_id,
        user_id=test_user.id,
        title="Título Actualizado",
        status=ConversationStatus.ACTIVE,
        metadata={},
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=[mock_renamed, True])
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_svc = MagicMock()
    app.dependency_overrides[get_session_service] = lambda: mock_svc

    # PATCH /api/v1/chat/conversations/{id}
    patch_resp = client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        json={"title": "Título Actualizado"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Título Actualizado"

    # DELETE /api/v1/chat/conversations/{id}
    del_resp = client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert del_resp.status_code == 204


def test_chat_turn_endpoint(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)

    saved_msg = SimpleNamespace(
        id=msg_id,
        conversation_id=conv_id,
        role=MessageRole.ASSISTANT,
        content="El Hospital San Juan gastó $50.000.000 en 2024.",
        model="gemini-2.5-flash",
        tokens_input=120,
        tokens_output=45,
        latency_ms=850.0,
        metadata={},
        created_at=now,
    )
    generated_mock = SimpleNamespace(
        content="El Hospital San Juan gastó $50.000.000 en 2024.",
        model="gemini-2.5-flash",
        latency_ms=850.0,
        token_usage={"tokens_input": 120, "tokens_output": 45, "retrieval_ms": 110.0},
        sources=[{"id": "doc-1", "title": "Licitación Hospitalaria", "relevance_score": 0.95}],
        citations=[{"source_id": "doc-1", "fact": "$50.000.000 gastados"}],
        grounding=SimpleNamespace(
            model_dump=lambda: {
                "supported": True,
                "grounding_ratio": 1.0,
                "unsupported_claims": [],
            }
        ),
    )

    mock_chat_svc = MagicMock()
    mock_chat_svc.execute_chat_turn = AsyncMock(return_value=(saved_msg, generated_mock))
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_svc

    resp = client.post(
        "/api/v1/chat",
        json={
            "conversation_id": str(conv_id),
            "message": "¿Cuánto gastó el Hospital San Juan?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # Check standard 9.27 proposed response fields
    assert data["conversation_id"] == str(conv_id)
    assert data["message_id"] == str(msg_id)
    assert "50.000.000" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["metrics"]["latency_ms"] == 850.0
    assert data["grounding"]["supported"] is True


def test_chat_stream_endpoint(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()

    async def mock_generator(*args, **kwargs):
        yield "event: status\ndata: {\"stage\": \"planning\"}\n\n"
        yield "event: token\ndata: {\"token\": \"Hola\"}\n\n"
        yield "event: done\ndata: {\"completed\": true}\n\n"

    mock_chat_svc = MagicMock()
    mock_chat_svc.stream_chat_turn = mock_generator
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_svc

    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": str(conv_id),
            "message": "¿Qué proveedores ganaron más licitaciones?",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in resp.text
    assert "event: token" in resp.text
    assert "event: done" in resp.text


def test_message_feedback_endpoint(client: TestClient, test_user: User) -> None:
    msg_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    fb_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)

    mock_fb = SimpleNamespace(
        id=fb_id,
        message_id=msg_id,
        conversation_id=conv_id,
        user_id=test_user.id,
        rating=1,
        reason=None,
        comment="Excelente respuesta y citas precisas",
        sources_used=[],
        retrieval_strategy="hybrid",
        model="gemini-2.5-flash",
        created_at=now,
    )

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(return_value=mock_fb)
    app.dependency_overrides[get_db] = lambda: mock_db

    resp = client.post(
        f"/api/v1/chat/messages/{msg_id}/feedback",
        json={
            "message_id": str(msg_id),
            "rating": 1,
            "comment": "Excelente respuesta y citas precisas",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == str(fb_id)
    assert data["message_id"] == str(msg_id)
    assert data["rating"] == 1


def test_unauthorized_conversation_access_returns_404(client: TestClient, test_user: User) -> None:
    conv_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=SessionAuthorizationError("Access denied"))
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_svc = MagicMock()
    mock_svc.aget_or_create_session = AsyncMock(side_effect=SessionAuthorizationError("Access denied"))
    app.dependency_overrides[get_session_service] = lambda: mock_svc

    # GET detail returns 404 (does not leak conversation existence)
    resp = client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert resp.status_code == 404

    # DELETE returns 404
    del_resp = client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert del_resp.status_code == 404
