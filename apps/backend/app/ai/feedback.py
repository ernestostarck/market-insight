"""Feedback Service for MercadoInsight AI (Fase 9.21).

Collects explicit user feedback (thumbs up / thumbs down, reason, commentary)
for assistant responses, along with snapshots of retrieval strategy and citations.

Architectural Rule:
Feedback is stored for offline evaluation, metric tracking and regression analysis.
It is NEVER directly piped into automated unsupervised model retraining.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import Conversation, Feedback, Message

logger = logging.getLogger(__name__)


class FeedbackService:
    """Handles recording and aggregation of AI response feedback."""

    def record_feedback(
        self,
        db: Session,
        message_id: UUID,
        user_id: UUID | None,
        rating: int,
        reason: str | None = None,
        comment: str | None = None,
    ) -> Feedback:
        """Record feedback for a specific assistant message."""
        # 1. Fetch target message
        msg_stmt = select(Message).where(Message.id == message_id)
        message = db.scalars(msg_stmt).first()
        if not message:
            raise ValueError(f"Mensaje no encontrado con id {message_id}")

        if message.role != "assistant":
            raise ValueError("El feedback solo puede aplicarse a respuestas del asistente.")

        # 2. Fetch conversation to verify ownership if user_id is provided
        conv_stmt = select(Conversation).where(Conversation.id == message.conversation_id)
        conv = db.scalars(conv_stmt).first()
        if conv and user_id and conv.user_id and conv.user_id != user_id:
            raise PermissionError("No autorizado para calificar mensajes de esta conversación.")

        # 3. Extract snapshot of sources, retrieval strategy and model from message metadata
        meta = message.metadata_ or {}
        sources_used = meta.get("sources", [])
        if not sources_used and "citations" in meta:
            sources_used = meta.get("citations", [])
        retrieval_strategy = meta.get("retrieval_strategy", "direct")
        model = message.model or meta.get("model", "unknown")

        feedback = Feedback(
            id=uuid4(),
            message_id=message.id,
            conversation_id=message.conversation_id,
            user_id=user_id,
            rating=1 if rating > 0 else -1,
            reason=reason,
            comment=comment,
            sources_used=sources_used,
            retrieval_strategy=retrieval_strategy,
            model=model,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        logger.info(
            "AI Feedback recorded: msg=%s, rating=%d, reason=%s",
            feedback.message_id,
            feedback.rating,
            feedback.reason,
        )

        return feedback

    def get_stats(self, db: Session) -> dict[str, Any]:
        """Aggregate feedback statistics across all conversations."""
        total = db.scalar(select(func.count(Feedback.id))) or 0
        pos = db.scalar(select(func.count(Feedback.id)).where(Feedback.rating > 0)) or 0
        neg = db.scalar(select(func.count(Feedback.id)).where(Feedback.rating < 0)) or 0

        # Reasons breakdown
        reasons_stmt = (
            select(Feedback.reason, func.count(Feedback.id))
            .where(Feedback.reason.is_not(None))
            .group_by(Feedback.reason)
        )
        reasons_rows = db.execute(reasons_stmt).all()
        reasons_breakdown = {str(r[0]): int(r[1]) for r in reasons_rows}

        positive_ratio = (pos / total) if total > 0 else 0.0

        return {
            "total_feedback": total,
            "positive_count": pos,
            "negative_count": neg,
            "positive_ratio": round(positive_ratio, 4),
            "reasons_breakdown": reasons_breakdown,
        }


_feedback_service: FeedbackService | None = None


def get_feedback_service() -> FeedbackService:
    """Singleton getter for FeedbackService."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
