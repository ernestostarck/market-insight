"""Dedicated Chat and Conversational RAG API Endpoints (Fase 9.27).

Exposes all conversational operations under /api/v1/chat:
- POST   /api/v1/chat
- POST   /api/v1/chat/stream
- GET    /api/v1/chat/conversations
- POST   /api/v1/chat/conversations
- GET    /api/v1/chat/conversations/{conversation_id}
- GET    /api/v1/chat/conversations/{conversation_id}/messages
- PATCH  /api/v1/chat/conversations/{conversation_id}
- DELETE /api/v1/chat/conversations/{conversation_id}
- POST   /api/v1/chat/messages/{message_id}/feedback
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat_service import ChatService
from app.ai.feedback import get_feedback_service
from app.ai.monitoring import AI_FEEDBACK_TOTAL
from app.ai.security import SecurityAuditLogger
from app.ai.session_service import (
    SessionAuthorizationError,
    SessionService,
    get_session_service,
)
from app.db.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    CreateFeedbackRequest,
    FeedbackResponse,
    MessageResponse,
    UpdateConversationRequest,
)

logger = logging.getLogger("ai.chat.api")

router = APIRouter()


def get_chat_service() -> ChatService:
    """Dependency provider for ChatService."""
    return ChatService()


# ---------------------------------------------------------------------------
# 1. POST /chat & POST /chat/stream
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Turno de conversación RAG completo (Fase 9.27)",
    description="Procesa una consulta en lenguaje natural con guardrails, memoria, recuperación híbrida y grounding.",
)
@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def chat_turn(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    chat_service: ChatService = Depends(get_chat_service),
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    request_id = req.headers.get("x-request-id") or str(uuid.uuid4())
    conv_id = request.conversation_id or uuid.uuid4()

    logger.info(
        "Chat turn initiated: request_id=%s, user_id=%s, conversation_id=%s",
        request_id,
        current_user.id,
        conv_id,
    )

    saved_msg, generated = await chat_service.execute_chat_turn(
        query=request.message,
        conversation_id=conv_id,
        user_id=current_user.id,
        db=session,
        session_service=session_service,
    )

    msg_resp = MessageResponse(
        id=saved_msg.id,
        conversation_id=saved_msg.conversation_id,
        role=saved_msg.role.value,
        content=saved_msg.content,
        model=saved_msg.model,
        tokens_input=saved_msg.tokens_input,
        tokens_output=saved_msg.tokens_output,
        latency_ms=saved_msg.latency_ms,
        metadata=saved_msg.metadata,
        created_at=saved_msg.created_at,
    )

    sources_list = [
        s.model_dump() if hasattr(s, "model_dump") else s for s in generated.sources
    ]
    citations_list = [
        c.model_dump() if hasattr(c, "model_dump") else c for c in generated.citations
    ]
    metrics_dict = {
        "latency_ms": generated.latency_ms or 0.0,
        "retrieval_ms": generated.token_usage.get("retrieval_ms", 180.0),
        "tokens_input": generated.token_usage.get("tokens_input", 0),
        "tokens_output": generated.token_usage.get("tokens_output", 0),
    }

    logger.info(
        "Chat turn completed: request_id=%s, latency_ms=%.2f, sources=%d",
        request_id,
        generated.latency_ms or 0.0,
        len(sources_list),
    )

    return ChatResponse(
        conversation_id=conv_id,
        message=msg_resp,
        message_id=saved_msg.id,
        answer=saved_msg.content,
        sources=sources_list,
        citations=citations_list,
        metrics=metrics_dict,
        grounding=generated.grounding.model_dump() if generated.grounding else None,
        sources_count=len(sources_list),
    )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Streaming de chat RAG vía Server-Sent Events (Fase 9.27)",
    description="Transmite eventos progresivos (status, token, citation, grounding, done) con soporte de abort/desconexión.",
)
async def chat_stream(
    req: Request,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    chat_service: ChatService = Depends(get_chat_service),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    conv_id = request.conversation_id or uuid.uuid4()

    generator = chat_service.stream_chat_turn(
        request=req,
        query=request.message,
        conversation_id=conv_id,
        user_id=current_user.id,
        db=session,
        session_service=session_service,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# 2. Conversations CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="Listar conversaciones del usuario",
    description="Recupera las sesiones de chat del usuario autenticado ordenadas por última actualización.",
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    def _list(sync_db: Any) -> list[Any]:
        return session_service.list_conversations(
            db=sync_db,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

    records = await session.run_sync(_list)
    return [
        ConversationResponse(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            status=c.status.value,
            metadata=c.metadata,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in records
    ]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva sesión de conversación",
    description="Inicializa una sesión conversacional aislada para el usuario actual.",
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conv_session = await session_service.aget_or_create_session(
        db=session,
        user_id=current_user.id,
        title=request.title,
        metadata=request.metadata,
    )
    return ConversationResponse(
        id=conv_session.id,
        user_id=conv_session.user_id,
        title=conv_session.title,
        status=conv_session.status.value,
        metadata=conv_session.metadata,
        created_at=conv_session.created_at,
        updated_at=conv_session.updated_at,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Obtener detalle y mensajes de conversación",
    description="Recupera la conversación con todos sus mensajes cronológicos previa validación de pertenencia.",
)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    try:
        conv_session = await session_service.aget_or_create_session(
            db=session,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
    except SessionAuthorizationError:
        # Security guideline: 404 to avoid leaking existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada o acceso denegado.",
        )

    def _get_msgs(sync_session: Any) -> list[Any]:
        return session_service.get_messages(
            db=sync_session,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )

    messages = await session.run_sync(_get_msgs)

    return ConversationDetailResponse(
        conversation=ConversationResponse(
            id=conv_session.id,
            user_id=conv_session.user_id,
            title=conv_session.title,
            status=conv_session.status.value,
            metadata=conv_session.metadata,
            created_at=conv_session.created_at,
            updated_at=conv_session.updated_at,
        ),
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role.value,
                content=m.content,
                model=m.model,
                tokens_input=m.tokens_input,
                tokens_output=m.tokens_output,
                latency_ms=m.latency_ms,
                metadata=m.metadata,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Obtener lista de mensajes de una conversación",
    description="Recupera únicamente el listado de mensajes pertenecientes a la conversación autorizada.",
)
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    def _get_msgs(sync_session: Any) -> list[Any]:
        return session_service.get_messages(
            db=sync_session,
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=limit,
        )

    try:
        messages = await session.run_sync(_get_msgs)
    except (ValueError, SessionAuthorizationError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada o acceso denegado.",
        )

    return [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role.value,
            content=m.content,
            model=m.model,
            tokens_input=m.tokens_input,
            tokens_output=m.tokens_output,
            latency_ms=m.latency_ms,
            metadata=m.metadata,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Renombrar conversación",
    description="Actualiza el título de una conversación existente del usuario.",
)
async def update_conversation(
    conversation_id: UUID,
    request: UpdateConversationRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    def _rename(sync_db: Any) -> Any:
        return session_service.rename_conversation(
            db=sync_db,
            conversation_id=conversation_id,
            title=request.title,
            user_id=current_user.id,
        )

    try:
        updated = await session.run_sync(_rename)
    except (ValueError, SessionAuthorizationError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada o acceso denegado.",
        )

    return ConversationResponse(
        id=updated.id,
        user_id=updated.user_id,
        title=updated.title,
        status=updated.status.value,
        metadata=updated.metadata,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar conversación",
    description="Elimina de forma permanente la conversación y sus mensajes asociados previa verificación de propiedad.",
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    session: AsyncSession = Depends(get_db),
) -> None:
    def _delete(sync_db: Any) -> bool:
        return session_service.delete_conversation(
            db=sync_db,
            conversation_id=conversation_id,
            user_id=current_user.id,
        )

    try:
        await session.run_sync(_delete)
    except (ValueError, SessionAuthorizationError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada o acceso denegado.",
        )

    SecurityAuditLogger.log_event(
        "conversation_deleted",
        current_user.id,
        conversation_id,
    )


# ---------------------------------------------------------------------------
# 3. Message Feedback
# ---------------------------------------------------------------------------


@router.post(
    "/messages/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar feedback sobre mensaje específico (Fase 9.27)",
    description="Permite calificar (+1 / -1) una respuesta del asistente con motivo opcional.",
)
async def message_feedback(
    message_id: UUID,
    request: CreateFeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    feedback_service = get_feedback_service()

    def _record(sync_db: Any) -> Any:
        return feedback_service.record_feedback(
            db=sync_db,
            message_id=message_id,
            user_id=current_user.id,
            rating=request.rating,
            reason=request.reason,
            comment=request.comment,
        )

    try:
        fb = await session.run_sync(_record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    AI_FEEDBACK_TOTAL.labels(
        rating="positive" if request.rating > 0 else "negative",
        reason=request.reason or "none",
    ).inc()

    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        conversation_id=fb.conversation_id,
        user_id=fb.user_id,
        rating=fb.rating,
        reason=fb.reason,
        comment=fb.comment,
        sources_used=fb.sources_used or [],
        retrieval_strategy=fb.retrieval_strategy,
        model=fb.model,
        created_at=fb.created_at,
    )
