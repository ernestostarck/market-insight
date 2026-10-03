"""create etl incremental checkpoints table

Revision ID: 20260806_0003
Revises: 20260806_0002
Create Date: 2026-08-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260806_0003"
down_revision = "20260806_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS etl")

    op.create_table(
        "etl_incremental_checkpoints",
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=64), nullable=False),
        sa.Column("marker", sa.String(length=128), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("source", "resource"),
        schema="etl",
    )

    op.create_index(
        "ix_etl_incremental_checkpoints_source_resource",
        "etl_incremental_checkpoints",
        ["source", "resource"],
        unique=True,
        schema="etl",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_etl_incremental_checkpoints_source_resource",
        table_name="etl_incremental_checkpoints",
        schema="etl",
    )
    op.drop_table("etl_incremental_checkpoints", schema="etl")
