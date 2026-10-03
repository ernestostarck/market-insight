"""add knowledge.product_concepts and knowledge.products (Fase 6.12 - Product & Attribute Extraction)

Revision ID: 20260828_0011
Revises: 20260828_0010
Create Date: 2026-08-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260828_0011"
down_revision = "20260828_0010"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


def upgrade() -> None:
    op.create_table(
        "product_concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("subcategory_id", sa.Integer(), nullable=False),
        sa.Column("dictionary_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", "dictionary_version", name="uq_knowledge_product_concepts_code_version"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_product_concepts_category_id", "product_concepts", ["category_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_product_concepts_subcategory_id", "product_concepts", ["subcategory_id"], schema=_SCHEMA)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("licitacion_item_id", sa.Integer(), nullable=False),
        sa.Column("product_concept_id", sa.Integer(), nullable=False),
        sa.Column("classification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cantidad", sa.Numeric(18, 4), nullable=True),
        sa.Column("unidad", sa.String(length=64), nullable=True),
        sa.Column("materiales", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dimensiones", sa.Text(), nullable=True),
        sa.Column("capacidad", sa.Text(), nullable=True),
        sa.Column("caracteristicas_tecnicas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["licitacion_item_id"], ["core.licitacion_item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_concept_id"], ["knowledge.product_concepts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classification_id"], ["knowledge.classifications.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("licitacion_item_id", "product_concept_id", name="uq_knowledge_products_item_concept"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_products_licitacion_id", "products", ["licitacion_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_table("products", schema=_SCHEMA)
    op.drop_table("product_concepts", schema=_SCHEMA)
