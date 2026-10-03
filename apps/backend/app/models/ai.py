"""SQLAlchemy ORM models for MercadoInsight AI conversations and messages (Fase 9.2).

Stored in the dedicated PostgreSQL schema 'ai'.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.core._types import jsonb_type


class Conversation(Base):
    """Conversational session entity stored permanently in PostgreSQL schema 'ai'."""

    __tablename__ = "conversation"
    __table_args__ = (
        Index("ix_ai_conversation_user_id", "user_id"),
        Index("ix_ai_conversation_created_at", "created_at"),
        {"schema": "ai"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_type(),
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """Individual message exchange within a conversation."""

    __tablename__ = "message"
    __table_args__ = (
        Index("ix_ai_message_conversation_created", "conversation_id", "created_at"),
        {"schema": "ai"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai.conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    tokens_input: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    tokens_output: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        jsonb_type(),
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class Feedback(Base):
    """User feedback for AI responses (Fase 9.21).

    Stored permanently in PostgreSQL schema 'ai'.
    Used for offline evaluation, quality monitoring and regression analysis.
    Rule: NEVER used for direct unsupervised automated retraining.
    """

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_ai_feedback_message_id", "message_id"),
        Index("ix_ai_feedback_conversation_id", "conversation_id"),
        Index("ix_ai_feedback_user_id", "user_id"),
        Index("ix_ai_feedback_created_at", "created_at"),
        {"schema": "ai"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai.message.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai.conversation.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    sources_used: Mapped[list[dict[str, Any]]] = mapped_column(
        jsonb_type(),
        default=list,
        nullable=False,
    )
    retrieval_strategy: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped[Message] = relationship(
        "Message",
        back_populates="feedbacks",
    )
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
    )
