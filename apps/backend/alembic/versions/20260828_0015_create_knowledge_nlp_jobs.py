"""create knowledge.nlp_jobs (Fase 6.20 - NLP Worker)

Revision ID: 20260828_0015
Revises: 20260828_0014
Create Date: 2026-08-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260828_0015"
down_revision = "20260828_0014"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


def upgrade() -> None:
    op.create_table(
        "nlp_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("completed_stages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pending_stages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key", name="uq_knowledge_nlp_jobs_idempotency_key"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_nlp_jobs_celery_task_id", "nlp_jobs", ["celery_task_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_nlp_jobs_idempotency_key", "nlp_jobs", ["idempotency_key"], schema=_SCHEMA)
    op.create_index("ix_knowledge_nlp_jobs_licitacion_id", "nlp_jobs", ["licitacion_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_nlp_jobs_status", "nlp_jobs", ["status"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_knowledge_nlp_jobs_status", table_name="nlp_jobs", schema=_SCHEMA)
    op.drop_index("ix_knowledge_nlp_jobs_licitacion_id", table_name="nlp_jobs", schema=_SCHEMA)
    op.drop_index("ix_knowledge_nlp_jobs_idempotency_key", table_name="nlp_jobs", schema=_SCHEMA)
    op.drop_index("ix_knowledge_nlp_jobs_celery_task_id", table_name="nlp_jobs", schema=_SCHEMA)
    op.drop_table("nlp_jobs", schema=_SCHEMA)
