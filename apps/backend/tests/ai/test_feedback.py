"""Unit tests for FeedbackService (Fase 9.21)."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.ai.feedback import FeedbackService
from app.models.ai import Conversation, Message


def test_record_feedback_positive():
    service = FeedbackService()

    msg_id = uuid4()
    conv_id = uuid4()
    user_id = uuid4()

    mock_msg = Message(
        id=msg_id,
        conversation_id=conv_id,
        role="assistant",
        content="Respuesta respaldada con fuentes.",
        model="gemini-2.5-flash",
        metadata_={
            "sources": [{"id": "1234-56-LP24", "title": "Sillas"}],
            "retrieval_strategy": "sql",
        },
    )

    mock_conv = Conversation(id=conv_id, user_id=user_id)

    mock_db = MagicMock()
    # Mock queries: first returns message, second returns conversation
    mock_db.scalars.return_value.first.side_effect = [mock_msg, mock_conv]

    feedback = service.record_feedback(
        db=mock_db,
        message_id=msg_id,
        user_id=user_id,
        rating=1,
        comment="Excelente respuesta",
    )

    assert feedback.rating == 1
    assert feedback.message_id == msg_id
    assert feedback.conversation_id == conv_id
    assert feedback.user_id == user_id
    assert feedback.model == "gemini-2.5-flash"
    assert feedback.retrieval_strategy == "sql"
    assert len(feedback.sources_used) == 1
    assert mock_db.add.called
    assert mock_db.commit.called


def test_record_feedback_negative_with_reason():
    service = FeedbackService()

    msg_id = uuid4()
    conv_id = uuid4()
    user_id = uuid4()

    mock_msg = Message(
        id=msg_id,
        conversation_id=conv_id,
        role="assistant",
        content="Respuesta con alucinación.",
        metadata_={},
    )
    mock_conv = Conversation(id=conv_id, user_id=user_id)

    mock_db = MagicMock()
    mock_db.scalars.return_value.first.side_effect = [mock_msg, mock_conv]

    feedback = service.record_feedback(
        db=mock_db,
        message_id=msg_id,
        user_id=user_id,
        rating=-1,
        reason="hallucination",
        comment="El monto indicado no aparece en las fuentes.",
    )

    assert feedback.rating == -1
    assert feedback.reason == "hallucination"
    assert "monto" in feedback.comment


def test_record_feedback_unauthorized_user_raises_permission_error():
    service = FeedbackService()

    msg_id = uuid4()
    conv_id = uuid4()
    owner_id = uuid4()
    intruder_id = uuid4()

    mock_msg = Message(id=msg_id, conversation_id=conv_id, role="assistant", content="Test")
    mock_conv = Conversation(id=conv_id, user_id=owner_id)

    mock_db = MagicMock()
    mock_db.scalars.return_value.first.side_effect = [mock_msg, mock_conv]

    with pytest.raises(PermissionError, match="No autorizado"):
        service.record_feedback(
            db=mock_db,
            message_id=msg_id,
            user_id=intruder_id,
            rating=1,
        )


def test_record_feedback_on_user_message_raises_value_error():
    service = FeedbackService()

    msg_id = uuid4()
    mock_msg = Message(id=msg_id, conversation_id=uuid4(), role="user", content="¿Pregunta?")

    mock_db = MagicMock()
    mock_db.scalars.return_value.first.return_value = mock_msg

    with pytest.raises(ValueError, match="asistente"):
        service.record_feedback(
            db=mock_db,
            message_id=msg_id,
            user_id=uuid4(),
            rating=1,
        )


def test_get_feedback_stats_aggregates_totals_and_reasons():
    service = FeedbackService()
    mock_db = MagicMock()

    # scalar calls for total, pos, neg
    mock_db.scalar.side_effect = [10, 8, 2]
    # execute call for reasons breakdown
    mock_db.execute.return_value.all.return_value = [
        ("hallucination", 1),
        ("outdated_info", 1),
    ]

    stats = service.get_stats(mock_db)

    assert stats["total_feedback"] == 10
    assert stats["positive_count"] == 8
    assert stats["negative_count"] == 2
    assert stats["positive_ratio"] == 0.8
    assert stats["reasons_breakdown"] == {"hallucination": 1, "outdated_info": 1}
