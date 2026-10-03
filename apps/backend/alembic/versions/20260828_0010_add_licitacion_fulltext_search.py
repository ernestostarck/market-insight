"""add full-text search (tsvector + GIN) on core.licitacion / core.licitacion_item (Fase 6.10 - Hybrid Search)

Revision ID: 20260828_0010
Revises: 20260828_0009
Create Date: 2026-08-28

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260828_0010"
down_revision = "20260828_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE core.licitacion ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('spanish', coalesce(nombre, '') || ' ' || coalesce(descripcion, ''))
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_core_licitacion_search_vector ON core.licitacion USING gin (search_vector)"
    )

    op.execute(
        """
        ALTER TABLE core.licitacion_item ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                to_tsvector('spanish', coalesce(nombre, '') || ' ' || coalesce(descripcion, ''))
            ) STORED
        """
    )
    op.execute(
        "CREATE INDEX ix_core_licitacion_item_search_vector ON core.licitacion_item USING gin (search_vector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS core.ix_core_licitacion_item_search_vector")
    op.execute("ALTER TABLE core.licitacion_item DROP COLUMN IF EXISTS search_vector")
    op.execute("DROP INDEX IF EXISTS core.ix_core_licitacion_search_vector")
    op.execute("ALTER TABLE core.licitacion DROP COLUMN IF EXISTS search_vector")
