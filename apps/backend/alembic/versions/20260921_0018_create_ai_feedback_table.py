"""create ai.feedback table (Fase 9.21 - AI Feedback)

Revision ID: 20260921_0018
Revises: 20260920_0017
Create Date: 2026-09-21

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260921_0018"
down_revision = "20260920_0017"
branch_labels = None
depends_on = None

_SCHEMA = "ai"


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "sources_used",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("retrieval_strategy", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["ai.message.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai.conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_index(
        "ix_ai_feedback_message_id",
        "feedback",
        ["message_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_ai_feedback_conversation_id",
        "feedback",
        ["conversation_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_ai_feedback_user_id",
        "feedback",
        ["user_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_ai_feedback_created_at",
        "feedback",
        ["created_at"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_feedback_created_at", table_name="feedback", schema=_SCHEMA)
    op.drop_index("ix_ai_feedback_user_id", table_name="feedback", schema=_SCHEMA)
    op.drop_index("ix_ai_feedback_conversation_id", table_name="feedback", schema=_SCHEMA)
    op.drop_index("ix_ai_feedback_message_id", table_name="feedback", schema=_SCHEMA)
    op.drop_table("feedback", schema=_SCHEMA)
