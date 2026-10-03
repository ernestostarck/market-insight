"""create staging raw ingestion events table

Revision ID: 20260806_0002
Revises: 20260806_0001
Create Date: 2026-08-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260806_0002"
down_revision = "20260806_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")

    op.create_table(
        "raw_ingestion_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="staging",
    )

    op.create_index(
        "ix_staging_raw_ingestion_events_id",
        "raw_ingestion_events",
        ["id"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_run_id",
        "raw_ingestion_events",
        ["ingestion_run_id"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_source",
        "raw_ingestion_events",
        ["source"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_resource",
        "raw_ingestion_events",
        ["resource"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_source_id",
        "raw_ingestion_events",
        ["source_id"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_payload_hash",
        "raw_ingestion_events",
        ["payload_hash"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_received_at",
        "raw_ingestion_events",
        ["received_at"],
        unique=False,
        schema="staging",
    )
    op.create_index(
        "ix_staging_raw_ingestion_events_source_resource",
        "raw_ingestion_events",
        ["source", "resource", "received_at"],
        unique=False,
        schema="staging",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staging_raw_ingestion_events_source_resource",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_received_at",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_payload_hash",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_source_id",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_resource",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_source",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_run_id",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_index(
        "ix_staging_raw_ingestion_events_id",
        table_name="raw_ingestion_events",
        schema="staging",
    )
    op.drop_table("raw_ingestion_events", schema="staging")
