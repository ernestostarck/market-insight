"""create knowledge schema (Fase 6.6 - Knowledge Layer)

Revision ID: 20260821_0008
Revises: 20260819_0007
Create Date: 2026-08-21

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

# revision identifiers, used by Alembic.
revision = "20260821_0008"
down_revision = "20260819_0007"
branch_labels = None
depends_on = None

_SCHEMA = "knowledge"


class _Vector(UserDefinedType):
    """PostgreSQL pgvector column. Mirrors app.models.knowledge.Vector."""

    cache_ok = True

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw: object) -> str:
        return f"VECTOR({self.dimensions})"


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}")

    # ------------------------------------------------------------------
    # knowledge.categories
    # ------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "taxonomy_version", name="uq_knowledge_categories_code_version"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # knowledge.subcategories
    # ------------------------------------------------------------------
    op.create_table(
        "subcategories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("category_id", "code", "taxonomy_version", name="uq_knowledge_subcategories_code_version"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_subcategories_category_id", "subcategories", ["category_id"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.concepts
    # ------------------------------------------------------------------
    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subcategory_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", "taxonomy_version", name="uq_knowledge_concepts_code_version"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_concepts_subcategory_id", "concepts", ["subcategory_id"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.keywords
    # ------------------------------------------------------------------
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("dictionary_version", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "term", "category_id", "subcategory_id", "taxonomy_version", "dictionary_version",
            name="uq_knowledge_keywords_scope",
        ),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_keywords_category_id", "keywords", ["category_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_keywords_subcategory_id", "keywords", ["subcategory_id"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.rules
    # ------------------------------------------------------------------
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", "version", name="uq_knowledge_rules_code_version"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_rules_category_id", "rules", ["category_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_rules_subcategory_id", "rules", ["subcategory_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_rules_active", "rules", ["active"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.model_versions
    # ------------------------------------------------------------------
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("artifact_uri", sa.String(length=2048), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_knowledge_model_versions_name_version"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_model_versions_status", "model_versions", ["status"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.dataset_versions
    # ------------------------------------------------------------------
    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_knowledge_dataset_versions_name_version"),
        schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # knowledge.documents
    # ------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("licitacion_id", "content_hash", name="uq_knowledge_documents_licitacion_hash"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_documents_licitacion_id", "documents", ["licitacion_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_documents_content_hash", "documents", ["content_hash"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.chunks
    # ------------------------------------------------------------------
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge.documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "sequence", name="uq_knowledge_chunks_document_sequence"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_chunks_document_id", "chunks", ["document_id"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.embeddings
    # ------------------------------------------------------------------
    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("vector", _Vector(384), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_version_id"], ["knowledge.model_versions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("licitacion_id", "content_hash", "model_version_id", name="uq_knowledge_embeddings_input_model"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_knowledge_embeddings_licitacion_model", "embeddings", ["licitacion_id", "model_version_id"], schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # knowledge.classifications
    # ------------------------------------------------------------------
    op.create_table(
        "classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("model_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column("rule_score", sa.Float(), nullable=True),
        sa.Column("model_score", sa.Float(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_version_id"], ["knowledge.model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["knowledge.dataset_versions.id"], ondelete="RESTRICT"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_classifications_licitacion_id", "classifications", ["licitacion_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_classifications_category_id", "classifications", ["category_id"], schema=_SCHEMA)
    op.create_index("ix_knowledge_classifications_subcategory_id", "classifications", ["subcategory_id"], schema=_SCHEMA)
    op.create_index(
        "ix_knowledge_classifications_licitacion_created", "classifications", ["licitacion_id", "created_at"], schema=_SCHEMA,
    )

    # ------------------------------------------------------------------
    # knowledge.entities
    # ------------------------------------------------------------------
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("classification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classification_id"], ["knowledge.classifications.id"], ondelete="SET NULL"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_entities_licitacion_type", "entities", ["licitacion_id", "entity_type"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.relationships
    # ------------------------------------------------------------------
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("licitacion_id", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("predicate", sa.String(length=64), nullable=False),
        sa.Column("object_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["licitacion_id"], ["core.licitacion.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["knowledge.entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_entity_id"], ["knowledge.entities.id"], ondelete="CASCADE"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_relationships_licitacion", "relationships", ["licitacion_id"], schema=_SCHEMA)

    # ------------------------------------------------------------------
    # knowledge.human_reviews
    # ------------------------------------------------------------------
    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("subcategory_id", sa.Integer(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *_timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["classification_id"], ["knowledge.classifications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge.categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["knowledge.subcategories.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("classification_id", "reviewer_id", name="uq_knowledge_reviews_classification_reviewer"),
        schema=_SCHEMA,
    )
    op.create_index("ix_knowledge_human_reviews_classification_id", "human_reviews", ["classification_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_table("human_reviews", schema=_SCHEMA)
    op.drop_table("relationships", schema=_SCHEMA)
    op.drop_table("entities", schema=_SCHEMA)
    op.drop_table("classifications", schema=_SCHEMA)
    op.drop_table("embeddings", schema=_SCHEMA)
    op.drop_table("chunks", schema=_SCHEMA)
    op.drop_table("documents", schema=_SCHEMA)
    op.drop_table("dataset_versions", schema=_SCHEMA)
    op.drop_table("model_versions", schema=_SCHEMA)
    op.drop_table("rules", schema=_SCHEMA)
    op.drop_table("keywords", schema=_SCHEMA)
    op.drop_table("concepts", schema=_SCHEMA)
    op.drop_table("subcategories", schema=_SCHEMA)
    op.drop_table("categories", schema=_SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE")
