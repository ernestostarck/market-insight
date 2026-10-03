"""create etl.etl_runs table (Fase 8.7 - ETL Monitoring)

Revision ID: 20260920_0016
Revises: 20260828_0015
Create Date: 2026-09-20

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260920_0016"
down_revision = "20260828_0015"
branch_labels = None
depends_on = None

_SCHEMA = "etl"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")

    op.create_table(
        "etl_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("pipeline", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="chilecompra_api"),
        sa.Column("trigger", sa.String(length=32), nullable=False, server_default="schedule"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("records_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
        schema=_SCHEMA,
    )

    op.create_index(
        "ix_etl_runs_pipeline",
        "etl_runs",
        ["pipeline"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_etl_runs_status",
        "etl_runs",
        ["status"],
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_etl_runs_started_at",
        "etl_runs",
        ["started_at"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_etl_runs_started_at", table_name="etl_runs", schema=_SCHEMA)
    op.drop_index("ix_etl_runs_status", table_name="etl_runs", schema=_SCHEMA)
    op.drop_index("ix_etl_runs_pipeline", table_name="etl_runs", schema=_SCHEMA)
    op.drop_table("etl_runs", schema=_SCHEMA)
