"""add knowledge.gold_labels (Fase 6.13 - Gold Dataset)

Revision ID: 20260828_0012
Revises: 20260828_0011
Create Date: 2026-08-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260828_0012"
down_revision = "20260828_0011"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


def upgrade() -> None:
    op.create_table(
        "gold_labels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("relevant", sa.Boolean(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=True),
        sa.Column("labeled_by", sa.String(length=255), nullable=True),
        sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("split", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["knowledge.dataset_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("dataset_version_id", "licitacion_id", name="uq_knowledge_gold_labels_dataset_licitacion"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_gold_labels_dataset_version_id", "gold_labels", ["dataset_version_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_gold_labels_split", "gold_labels", ["split"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_table("gold_labels", schema=_SCHEMA)
