"""add relevant and relevance_tier to knowledge.human_reviews (Fase 6.17 - Confidence & Human-in-the-Loop)

Revision ID: 20260828_0014
Revises: 20260828_0013
Create Date: 2026-08-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260828_0014"
down_revision = "20260828_0013"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


def upgrade() -> None:
    op.add_column("human_reviews", sa.Column("relevant", sa.Boolean(), nullable=True), schema=_SCHEMA)
    op.add_column("human_reviews", sa.Column("relevance_tier", sa.String(length=16), nullable=True), schema=_SCHEMA)


def downgrade() -> None:
    op.drop_column("human_reviews", "relevance_tier", schema=_SCHEMA)
    op.drop_column("human_reviews", "relevant", schema=_SCHEMA)
