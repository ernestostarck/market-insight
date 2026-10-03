"""add HNSW vector index on knowledge.embeddings (Fase 6.9 - pgvector)

Revision ID: 20260828_0009
Revises: 20260821_0008
Create Date: 2026-08-28

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260828_0009"
down_revision = "20260821_0008"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_knowledge_embeddings_vector_hnsw"


def upgrade() -> None:
    # Defensive/idempotent — the extension is already bootstrapped via
    # docker/postgres/init/001-extensions.sql (Fase 1.3), but this keeps the
    # migration self-sufficient for any environment that skips that script.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # HNSW over ivfflat: knowledge.embeddings has 0 rows in production today
    # (6.7/6.8 just landed) — ivfflat's "lists" parameter needs existing data
    # to calibrate well, HNSW builds incrementally and is effective from the
    # first row. vector_cosine_ops matches EmbeddingService's normalized
    # vectors and the `<=>` operator used by VectorSearchRepository.
    op.execute(
        f"CREATE INDEX {_INDEX_NAME} ON knowledge.embeddings "
        "USING hnsw (vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS knowledge.{_INDEX_NAME}")
