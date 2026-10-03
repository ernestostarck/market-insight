"""create adjudicacion analytics snapshots table

Revision ID: 20260806_0001
Revises:
Create Date: 2026-08-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260806_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "adjudicacion_analytics_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opportunity_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("is_outlier", sa.Boolean(), nullable=False),
        sa.Column("reasons", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("award_ratio", sa.Float(), nullable=True),
        sa.Column("awarded_amount", sa.Float(), nullable=True),
        sa.Column(
            "quality_flags", postgresql.JSON(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "source_filters", postgresql.JSON(astext_type=sa.Text()), nullable=False
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
        sa.PrimaryKeyConstraint("id"),
        schema="analytics",
    )

    op.create_index(
        "ix_analytics_adjudicacion_snapshots_id",
        "adjudicacion_analytics_snapshots",
        ["id"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_analytics_adjudicacion_snapshots_external_id",
        "adjudicacion_analytics_snapshots",
        ["external_id"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_analytics_adjudicacion_snapshots_snapshot_date",
        "adjudicacion_analytics_snapshots",
        ["snapshot_date"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_analytics_adjudicacion_snapshots_scored_at",
        "adjudicacion_analytics_snapshots",
        ["scored_at"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_analytics_adjudicacion_snapshots_risk_level",
        "adjudicacion_analytics_snapshots",
        ["risk_level"],
        unique=False,
        schema="analytics",
    )
    op.create_index(
        "ix_analytics_adjudicacion_snapshots_external_date",
        "adjudicacion_analytics_snapshots",
        ["external_id", "snapshot_date"],
        unique=False,
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_external_date",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_risk_level",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_scored_at",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_snapshot_date",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_external_id",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_index(
        "ix_analytics_adjudicacion_snapshots_id",
        table_name="adjudicacion_analytics_snapshots",
        schema="analytics",
    )
    op.drop_table("adjudicacion_analytics_snapshots", schema="analytics")
