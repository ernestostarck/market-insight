"""Session Management and Concurrency Control for MercadoInsight AI (Fase 9.3).

Combines permanent, durable storage in PostgreSQL (schema 'ai') with ephemeral
state caching and distributed locking in Redis to handle concurrency, authorization,
and session lifecycle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.ai.contracts import (
    ChatMessage,
    ConversationSession,
    ConversationStatus,
    MessageRole,
)
from app.models.ai import Conversation, Message

logger = logging.getLogger(__name__)

# Ephemeral session TTL in Redis (24 hours)
_SESSION_TTL_SECONDS: int = 24 * 3600
_LOCK_TTL_SECONDS: int = 30


class SessionAuthorizationError(PermissionError):
    """Raised when a user attempts to access a conversation they do not own."""


class SessionConcurrencyError(RuntimeError):
    """Raised when another operation is currently locking the conversation."""


class SessionService:
    """Service managing conversational session lifecycle, authorization, and concurrency."""

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        session_ttl: int = _SESSION_TTL_SECONDS,
        lock_ttl: int = _LOCK_TTL_SECONDS,
    ) -> None:
        self._redis = redis_client
        self._session_ttl = session_ttl
        self._lock_ttl = lock_ttl

    def _session_key(self, conversation_id: UUID) -> str:
        return f"ai:session:{conversation_id}"

    def _lock_key(self, conversation_id: UUID) -> str:
        return f"ai:lock:conversation:{conversation_id}"

    # -------------------------------------------------------------------------
    # 1. Ephemeral Redis Cache (Metadata only - Never full messages)
    # -------------------------------------------------------------------------

    async def _cache_session_state(
        self,
        conversation_id: UUID,
        user_id: UUID | None,
        title: str | None,
        status: str,
        created_at: datetime | None,
    ) -> None:
        """Store lightweight session metadata in Redis without message history."""
        if self._redis is None:
            return

        created_dt = created_at or datetime.now(UTC)
        payload = {
            "conversation_id": str(conversation_id),
            "user_id": str(user_id) if user_id else None,
            "title": title,
            "status": status,
            "created_at": created_dt.isoformat(),
            "last_activity_at": datetime.now(UTC).isoformat(),
        }
        try:
            await self._redis.set(
                self._session_key(conversation_id),
                json.dumps(payload),
                ex=self._session_ttl,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to cache AI session in Redis: %s", exc)

    async def _touch_session(self, conversation_id: UUID) -> None:
        """Refresh session TTL and update last activity timestamp in Redis."""
        if self._redis is None:
            return
        key = self._session_key(conversation_id)
        try:
            raw = await self._redis.get(key)
            if raw:
                data = json.loads(raw)
                data["last_activity_at"] = datetime.now(UTC).isoformat()
                await self._redis.set(key, json.dumps(data), ex=self._session_ttl)
            else:
                await self._redis.expire(key, self._session_ttl)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to touch AI session in Redis: %s", exc)

    # -------------------------------------------------------------------------
    # 2. Concurrency Control (Distributed Lock)
    # -------------------------------------------------------------------------

    @asynccontextmanager
    async def acquire_conversation_lock(
        self,
        conversation_id: UUID,
        timeout: float = 5.0,
    ) -> AsyncIterator[str]:
        """Acquire an exclusive distributed lock for the conversation.

        Guarantees that parallel requests do not interleave message mutations.
        """
        lock_token = str(uuid.uuid4())
        key = self._lock_key(conversation_id)

        if self._redis is not None:
            acquired = False
            start = datetime.now(UTC)
            while (datetime.now(UTC) - start).total_seconds() < timeout:
                try:
                    res = await self._redis.set(key, lock_token, nx=True, ex=self._lock_ttl)
                    if res:
                        acquired = True
                        break
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Redis lock error: %s", exc)
                    break
                await asyncio.sleep(0.05)

            if not acquired:
                raise SessionConcurrencyError(
                    f"Conversation {conversation_id} is currently locked by another concurrent process."
                )

        try:
            yield lock_token
        finally:
            if self._redis is not None:
                try:
                    # Release lock if value matches
                    lua_release = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    await self._redis.eval(lua_release, 1, key, lock_token)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Failed to release lock %s: %s", key, exc)

    # -------------------------------------------------------------------------
    # 3. Session Operations (PostgreSQL Permanent Storage)
    # -------------------------------------------------------------------------

    def get_or_create_session(
        self,
        db: Session,
        conversation_id: UUID | None = None,
        user_id: UUID | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        """Synchronous session lookup or creation for standard DB sessions."""
        meta = metadata or {}

        if conversation_id is not None:
            conv = db.scalar(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            if conv is not None:
                # Authorization check: user cannot access other user's private session
                if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
                    raise SessionAuthorizationError(
                        f"User {user_id} is not authorized to access conversation {conversation_id}."
                    )
                return ConversationSession(
                    id=conv.id,
                    user_id=conv.user_id,
                    title=conv.title,
                    status=ConversationStatus(conv.status),
                    metadata=conv.metadata_ or {},
                    created_at=conv.created_at or datetime.now(UTC),
                    updated_at=conv.updated_at or datetime.now(UTC),
                )

        # Create new conversation in PostgreSQL
        new_id = conversation_id or uuid.uuid4()
        now = datetime.now(UTC)
        conv = Conversation(
            id=new_id,
            user_id=user_id,
            title=title or "Nueva consulta",
            status="active",
            metadata_=meta,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        return ConversationSession(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            status=ConversationStatus(conv.status),
            metadata=conv.metadata_ or {},
            created_at=conv.created_at or now,
            updated_at=conv.updated_at or now,
        )

    async def aget_or_create_session(
        self,
        db: AsyncSession,
        conversation_id: UUID | None = None,
        user_id: UUID | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationSession:
        """Asynchronous session lookup or creation."""
        meta = metadata or {}

        if conversation_id is not None:
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await db.execute(stmt)
            conv = result.scalar_one_or_none()
            if conv is not None:
                # Authorization check
                if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
                    raise SessionAuthorizationError(
                        f"User {user_id} is not authorized to access conversation {conversation_id}."
                    )
                await self._touch_session(conv.id)
                return ConversationSession(
                    id=conv.id,
                    user_id=conv.user_id,
                    title=conv.title,
                    status=ConversationStatus(conv.status),
                    metadata=conv.metadata_ or {},
                    created_at=conv.created_at or datetime.now(UTC),
                    updated_at=conv.updated_at or datetime.now(UTC),
                )

        # Create new conversation
        new_id = conversation_id or uuid.uuid4()
        now = datetime.now(UTC)
        conv = Conversation(
            id=new_id,
            user_id=user_id,
            title=title or "Nueva consulta",
            status="active",
            metadata_=meta,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

        await self._cache_session_state(
            conversation_id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            status=conv.status,
            created_at=conv.created_at or now,
        )

        return ConversationSession(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            status=ConversationStatus(conv.status),
            metadata=conv.metadata_ or {},
            created_at=conv.created_at or now,
            updated_at=conv.updated_at or now,
        )

    # -------------------------------------------------------------------------
    # 4. Message History Operations
    # -------------------------------------------------------------------------

    def save_message(
        self,
        db: Session,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        user_id: UUID | None = None,
        model: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """Synchronously persist message in PostgreSQL and touch session."""
        conv = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} does not exist.")

        if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
            raise SessionAuthorizationError(
                f"User {user_id} is not authorized to write to conversation {conversation_id}."
            )

        msg = Message(
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            metadata_=metadata or {},
        )
        db.add(msg)
        conv.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(msg)

        return ChatMessage(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=MessageRole(msg.role),
            content=msg.content,
            model=msg.model,
            tokens_input=msg.tokens_input,
            tokens_output=msg.tokens_output,
            latency_ms=msg.latency_ms,
            metadata=msg.metadata_ or {},
            created_at=msg.created_at or datetime.now(UTC),
        )

    def get_messages(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """Synchronously retrieve conversation messages ordered chronologically."""
        conv = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} does not exist.")

        if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
            raise SessionAuthorizationError(
                f"User {user_id} is not authorized to view conversation {conversation_id}."
            )

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        records = db.scalars(stmt).all()
        return [
            ChatMessage(
                id=m.id,
                conversation_id=m.conversation_id,
                role=MessageRole(m.role),
                content=m.content,
                model=m.model,
                tokens_input=m.tokens_input,
                tokens_output=m.tokens_output,
                latency_ms=m.latency_ms,
                metadata=m.metadata_ or {},
                created_at=m.created_at or datetime.now(UTC),
            )
            for m in records
        ]

    def list_conversations(
        self,
        db: Session,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSession]:
        """List active conversations belonging to the specified user."""
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        records = db.scalars(stmt).all()
        return [
            ConversationSession(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                status=ConversationStatus(c.status),
                metadata=c.metadata_ or {},
                created_at=c.created_at or datetime.now(UTC),
                updated_at=c.updated_at or datetime.now(UTC),
            )
            for c in records
        ]

    def delete_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """Delete conversation and cascaded messages, validating ownership."""
        conv = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} does not exist.")

        if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
            raise SessionAuthorizationError(
                f"User {user_id} is not authorized to delete conversation {conversation_id}."
            )

        db.delete(conv)
        db.commit()
        return True

    def rename_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        title: str,
        user_id: UUID | None = None,
    ) -> ConversationSession:
        """Rename an existing conversation."""
        conv = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} does not exist.")

        if conv.user_id is not None and user_id is not None and conv.user_id != user_id:
            raise SessionAuthorizationError(
                f"User {user_id} is not authorized to rename conversation {conversation_id}."
            )

        conv.title = title
        conv.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(conv)

        return ConversationSession(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            status=ConversationStatus(conv.status),
            metadata=conv.metadata_ or {},
            created_at=conv.created_at or datetime.now(UTC),
            updated_at=conv.updated_at or datetime.now(UTC),
        )



_session_service_instance: SessionService | None = None


def get_session_service() -> SessionService:
    """Dependency provider for SessionService."""
    global _session_service_instance
    if _session_service_instance is None:
        from app.core.settings import get_settings

        settings = get_settings()
        try:
            redis_client = aioredis.from_url(settings.redis_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not initialize Redis client for SessionService: %s", exc)
            redis_client = None
        _session_service_instance = SessionService(redis_client=redis_client)
    return _session_service_instance

