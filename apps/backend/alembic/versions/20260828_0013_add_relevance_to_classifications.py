"""add relevance_score/relevance_tier to knowledge.classifications (Fase 6.16 - Market Relevance)

Revision ID: 20260828_0013
Revises: 20260828_0012
Create Date: 2026-08-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260828_0013"
down_revision = "20260828_0012"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


def upgrade() -> None:
    op.add_column("classifications", sa.Column("relevance_score", sa.Float(), nullable=True), schema=_SCHEMA)
    op.add_column("classifications", sa.Column("relevance_tier", sa.String(length=16), nullable=True), schema=_SCHEMA)


def downgrade() -> None:
    op.drop_column("classifications", "relevance_tier", schema=_SCHEMA)
    op.drop_column("classifications", "relevance_score", schema=_SCHEMA)
