"""Unit tests for ChatService and SSE Streaming (Fase 9.20)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.chat_service import ChatService
from app.ai.contracts import (
    ChatMessage,
    ConversationSession,
    MessageRole,
    RetrievalResult,
    RetrievalStrategy,
    Source,
)
from app.ai.interfaces import LLMGateway
from app.ai.session_service import SessionService


@pytest.fixture
def mock_session_service() -> MagicMock:
    service = MagicMock(spec=SessionService)
    service.acquire_conversation_lock = MagicMock()

    # Async context manager for acquire_conversation_lock
    class AsyncLockCtx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    service.acquire_conversation_lock.return_value = AsyncLockCtx()

    async def _mock_aget_or_create(db, conversation_id, user_id):
        return ConversationSession(id=conversation_id, user_id=user_id)

    service.aget_or_create_session = AsyncMock(side_effect=_mock_aget_or_create)
    service.get_messages = MagicMock(return_value=[])

    def _mock_save(*args, **kwargs):
        return ChatMessage(
            id=uuid4(),
            conversation_id=kwargs.get("conversation_id", uuid4()),
            role=kwargs.get("role", MessageRole.ASSISTANT),
            content=kwargs.get("content", "Respuesta simulada"),
        )

    service.save_message = MagicMock(side_effect=_mock_save)
    return service


@pytest.mark.asyncio
async def test_execute_chat_turn_success(mock_session_service: MagicMock):
    mock_llm = AsyncMock(spec=LLMGateway)
    mock_llm.generate_response.return_value = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="Respuesta sobre licitaciones de sillas de ruedas.",
        tokens_input=50,
        tokens_output=20,
        latency_ms=150.0,
    )

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = RetrievalResult(
        strategy_used=RetrievalStrategy.DIRECT,
        items=[{"id": "1234-56-LP24", "title": "Sillas de ruedas"}],
        sources=[
            Source(
                id="1234-56-LP24",
                source_type="tender",
                title="Licitación Sillas de Ruedas",
                snippet="Adquisición de sillas de ruedas para Hospital Central.",
            )
        ],
        total_results=1,
    )

    chat_service = ChatService(llm_gateway=mock_llm, retriever=mock_retriever)

    mock_db = AsyncMock()
    # Mock run_sync to immediately execute the sync callable
    mock_db.run_sync = AsyncMock(side_effect=lambda fn: fn(MagicMock()))

    conv_id = uuid4()
    user_id = uuid4()

    saved_msg, generated = await chat_service.execute_chat_turn(
        query="Licitaciones de sillas de ruedas en Santiago",
        conversation_id=conv_id,
        user_id=user_id,
        db=mock_db,
        session_service=mock_session_service,
    )

    assert saved_msg is not None
    assert generated is not None
    assert "sillas de ruedas" in generated.content
    assert mock_session_service.save_message.call_count == 2  # 1 user + 1 assistant


@pytest.mark.asyncio
async def test_stream_chat_turn_emits_sse_events(mock_session_service: MagicMock):
    mock_llm = AsyncMock(spec=LLMGateway)
    mock_llm.generate_response.return_value = ChatMessage(
        role=MessageRole.ASSISTANT,
        content="Respuesta en streaming de prueba.",
        tokens_input=30,
        tokens_output=15,
        latency_ms=100.0,
    )

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = RetrievalResult(
        strategy_used=RetrievalStrategy.DIRECT,
        items=[{"id": "1234-56-LP24", "title": "Licitación de prueba"}],
        sources=[
            Source(
                id="1234-56-LP24",
                source_type="tender",
                title="Licitación de prueba",
                snippet="Detalles de licitación de prueba.",
            )
        ],
        total_results=1,
    )

    chat_service = ChatService(llm_gateway=mock_llm, retriever=mock_retriever)

    mock_db = AsyncMock()
    mock_db.run_sync = AsyncMock(side_effect=lambda fn: fn(MagicMock()))

    # Mock Request
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    conv_id = uuid4()
    user_id = uuid4()

    event_chunks: list[str] = []
    async for chunk in chat_service.stream_chat_turn(
        request=mock_request,
        query="Licitaciones de prueba",
        conversation_id=conv_id,
        user_id=user_id,
        db=mock_db,
        session_service=mock_session_service,
    ):
        event_chunks.append(chunk)

    all_events = "".join(event_chunks)

    # Check that required SSE events are present
    assert "event: status" in all_events
    assert "event: token" in all_events
    assert "event: done" in all_events
    assert "Respuesta" in all_events


@pytest.mark.asyncio
async def test_stream_chat_turn_aborts_on_client_disconnect(mock_session_service: MagicMock):
    chat_service = ChatService()

    # Request simulates immediate disconnection
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=True)

    mock_db = AsyncMock()

    event_chunks: list[str] = []
    async for chunk in chat_service.stream_chat_turn(
        request=mock_request,
        query="Consulta cancelada",
        conversation_id=uuid4(),
        user_id=uuid4(),
        db=mock_db,
        session_service=mock_session_service,
    ):
        event_chunks.append(chunk)

    # Should only emit the initial event and exit immediately
    assert len(event_chunks) == 1
    assert "event: status" in event_chunks[0]
    # Generation must not have persisted messages
    mock_session_service.save_message.assert_not_called()
