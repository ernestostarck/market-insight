"""API request and response schemas for MercadoInsight AI (Fase 9)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    """Payload to create a new conversational session."""

    title: str | None = Field(default=None, description="Optional title for the conversation.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes.")


class ConversationResponse(BaseModel):
    """Response model representing a conversation session."""

    id: UUID
    user_id: UUID | None = None
    title: str | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CreateMessageRequest(BaseModel):
    """Payload to append a message to a conversation."""

    role: str = Field(default="user", description="Sender role (user, system, assistant, tool).")
    content: str = Field(..., description="Message text content.")
    model: str | None = Field(default=None, description="LLM model identifier.")
    tokens_input: int | None = None
    tokens_output: int | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Response model representing a single message."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """Detailed view of a conversation including historical messages."""

    conversation: ConversationResponse
    messages: list[MessageResponse] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Payload to execute an evidence-grounded chat turn."""

    conversation_id: UUID | None = Field(default=None, description="Optional conversation UUID; creates new if omitted.")
    message: str = Field(..., description="User question or query.")
    stream: bool = Field(default=False, description="Whether to stream response as SSE.")


class UpdateConversationRequest(BaseModel):
    """Payload to update conversation metadata or rename."""

    title: str = Field(..., min_length=1, max_length=255, description="Updated conversation title.")


class ChatResponse(BaseModel):
    """End-to-end grounded assistant response with citations and metadata."""

    conversation_id: UUID
    message: MessageResponse
    message_id: UUID | None = None
    answer: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    grounding: dict[str, Any] | None = None
    sources_count: int = 0


class CreateFeedbackRequest(BaseModel):
    """Payload to register user feedback for an AI response (Fase 9.21)."""

    message_id: UUID = Field(..., description="Target assistant message UUID.")
    rating: int = Field(..., ge=-1, le=1, description="1 for thumbs up (+1), -1 for thumbs down (-1).")
    reason: str | None = Field(
        default=None,
        description="Optional reason (e.g. hallucination, outdated, wrong_sources, irrelevant, incomplete).",
    )
    comment: str | None = Field(default=None, max_length=1000, description="Optional user commentary.")


class FeedbackResponse(BaseModel):
    """Stored feedback model representation."""

    id: UUID
    message_id: UUID
    conversation_id: UUID
    user_id: UUID | None = None
    rating: int
    reason: str | None = None
    comment: str | None = None
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_strategy: str | None = None
    model: str | None = None
    created_at: datetime


class FeedbackStatsResponse(BaseModel):
    """Aggregated feedback metrics."""

    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    positive_ratio: float = 0.0
    reasons_breakdown: dict[str, int] = Field(default_factory=dict)


class CostSummaryResponse(BaseModel):
    """Summary of AI tokens usage and costs (Fase 9.24)."""

    total_cost_usd: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens: int = 0
    by_model: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_intent: dict[str, float] = Field(default_factory=dict)

