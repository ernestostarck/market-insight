"""create ai.conversation and ai.message tables (Fase 9.2 - Conversational AI)

Revision ID: 20260920_0017
Revises: 20260920_0016
Create Date: 2026-09-20

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260920_0017"
down_revision = "20260920_0016"
branch_labels = None
depends_on = None

_SCHEMA = "ai"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")

    # 1. Create ai.conversation table
    op.create_table(
        "conversation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_index(
        "ix_ai_conversation_user_id",
        "conversation",
        ["user_id"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_ai_conversation_created_at",
        "conversation",
        ["created_at"],
        schema=_SCHEMA,
    )

    # 2. Create ai.message table
    op.create_table(
        "message",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            [f"{_SCHEMA}.conversation.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=_SCHEMA,
    )

    op.create_index(
        "ix_ai_message_conversation_created",
        "message",
        ["conversation_id", "created_at"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_message_conversation_created", table_name="message", schema=_SCHEMA)
    op.drop_table("message", schema=_SCHEMA)
    op.drop_index("ix_ai_conversation_created_at", table_name="conversation", schema=_SCHEMA)
    op.drop_index("ix_ai_conversation_user_id", table_name="conversation", schema=_SCHEMA)
    op.drop_table("conversation", schema=_SCHEMA)
