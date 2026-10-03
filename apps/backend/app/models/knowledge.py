"""Persistent semantic knowledge generated from canonical tenders."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.base import Base
from app.models.core._types import jsonb_type


class Vector(UserDefinedType):
    """PostgreSQL pgvector column, with a fixed dimension set by the model."""

    cache_ok = True

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **kw: object) -> str:
        return f"VECTOR({self.dimensions})"


class _Timestamped(Base):
    __abstract__ = True
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Document(_Timestamped):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("licitacion_id", "content_hash", name="uq_knowledge_documents_licitacion_hash"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class Chunk(_Timestamped):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "sequence", name="uq_knowledge_chunks_document_sequence"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.documents.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)


class Category(_Timestamped):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("code", "taxonomy_version", name="uq_knowledge_categories_code_version"), {"schema": "knowledge"})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subcategory(_Timestamped):
    __tablename__ = "subcategories"
    __table_args__ = (UniqueConstraint("category_id", "code", "taxonomy_version", name="uq_knowledge_subcategories_code_version"), {"schema": "knowledge"})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Concept(_Timestamped):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("code", "taxonomy_version", name="uq_knowledge_concepts_code_version"), {"schema": "knowledge"})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subcategory_id: Mapped[int] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ModelVersion(_Timestamped):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_knowledge_model_versions_name_version"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    artifact_uri: Mapped[str | None] = mapped_column(String(2048))
    parameters: Mapped[dict | None] = mapped_column(jsonb_type())
    metrics: Mapped[dict | None] = mapped_column(jsonb_type())


class DatasetVersion(_Timestamped):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_knowledge_dataset_versions_name_version"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict | None] = mapped_column(jsonb_type())


class Keyword(_Timestamped):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint(
            "term", "category_id", "subcategory_id", "taxonomy_version", "dictionary_version",
            name="uq_knowledge_keywords_scope",
        ),
        {"schema": "knowledge"},
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"), index=True)
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    # Independent from taxonomy_version: a dictionary release can target an existing
    # taxonomy version, and a new taxonomy version needs dictionary re-review before
    # promotion. See docs/07-ai/semantic-dictionary.md.
    dictionary_version: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Rule(_Timestamped):
    __tablename__ = "rules"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_knowledge_rules_code_version"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"), index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class Embedding(_Timestamped):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("licitacion_id", "content_hash", "model_version_id", name="uq_knowledge_embeddings_input_model"),
        Index("ix_knowledge_embeddings_licitacion_model", "licitacion_id", "model_version_id"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.model_versions.id", ondelete="RESTRICT"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)


class Classification(_Timestamped):
    __tablename__ = "classifications"
    __table_args__ = (Index("ix_knowledge_classifications_licitacion_created", "licitacion_id", "created_at"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"), index=True)
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"), index=True)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge.model_versions.id", ondelete="RESTRICT"))
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge.dataset_versions.id", ondelete="RESTRICT"))
    taxonomy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_score: Mapped[float | None] = mapped_column(Float)
    model_score: Mapped[float | None] = mapped_column(Float)
    similarity_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    relevance_tier: Mapped[str | None] = mapped_column(String(16))
    explanation: Mapped[dict | None] = mapped_column(jsonb_type())


class Entity(_Timestamped):
    __tablename__ = "entities"
    __table_args__ = (Index("ix_knowledge_entities_licitacion_type", "licitacion_id", "entity_type"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False)
    classification_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge.classifications.id", ondelete="SET NULL"))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)


class Relationship(_Timestamped):
    __tablename__ = "relationships"
    __table_args__ = (Index("ix_knowledge_relationships_licitacion", "licitacion_id"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False)
    subject_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.entities.id", ondelete="CASCADE"), nullable=False)
    predicate: Mapped[str] = mapped_column(String(64), nullable=False)
    object_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.entities.id", ondelete="CASCADE"), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)


class ProductConcept(_Timestamped):
    __tablename__ = "product_concepts"
    __table_args__ = (UniqueConstraint("code", "dictionary_version", name="uq_knowledge_product_concepts_code_version"), {"schema": "knowledge"})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    subcategory_id: Mapped[int] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"), nullable=False, index=True)
    dictionary_version: Mapped[str] = mapped_column(String(64), nullable=False)


class Product(_Timestamped):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_knowledge_products_licitacion_id", "licitacion_id"),
        UniqueConstraint("licitacion_item_id", "product_concept_id", name="uq_knowledge_products_item_concept"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False)
    licitacion_item_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion_item.id", ondelete="CASCADE"), nullable=False)
    product_concept_id: Mapped[int] = mapped_column(ForeignKey("knowledge.product_concepts.id", ondelete="RESTRICT"), nullable=False)
    classification_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("knowledge.classifications.id", ondelete="SET NULL"))
    cantidad: Mapped[float | None] = mapped_column(Numeric(18, 4))
    unidad: Mapped[str | None] = mapped_column(String(64))
    materiales: Mapped[list | None] = mapped_column(jsonb_type())
    dimensiones: Mapped[str | None] = mapped_column(Text)
    capacidad: Mapped[str | None] = mapped_column(Text)
    caracteristicas_tecnicas: Mapped[list | None] = mapped_column(jsonb_type())
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)


class GoldLabel(_Timestamped):
    __tablename__ = "gold_labels"
    __table_args__ = (
        Index("ix_knowledge_gold_labels_dataset_version_id", "dataset_version_id"),
        Index("ix_knowledge_gold_labels_split", "split"),
        UniqueConstraint("dataset_version_id", "licitacion_id", name="uq_knowledge_gold_labels_dataset_licitacion"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.dataset_versions.id", ondelete="CASCADE"), nullable=False)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False)
    relevant: Mapped[bool | None] = mapped_column(Boolean)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"))
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"))
    taxonomy_version: Mapped[str | None] = mapped_column(String(64))
    labeled_by: Mapped[str | None] = mapped_column(String(255))
    labeled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    split: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text)


class HumanReview(_Timestamped):
    __tablename__ = "human_reviews"
    __table_args__ = (UniqueConstraint("classification_id", "reviewer_id", name="uq_knowledge_reviews_classification_reviewer"), {"schema": "knowledge"})
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    classification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge.classifications.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.categories.id", ondelete="RESTRICT"))
    subcategory_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.subcategories.id", ondelete="RESTRICT"))
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    relevant: Mapped[bool | None] = mapped_column(Boolean)
    relevance_tier: Mapped[str | None] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text)


class NLPJob(_Timestamped):
    __tablename__ = "nlp_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_knowledge_nlp_jobs_idempotency_key"),
        {"schema": "knowledge"},
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    licitacion_id: Mapped[int] = mapped_column(ForeignKey("core.licitacion.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    completed_stages: Mapped[list | None] = mapped_column(jsonb_type())
    pending_stages: Mapped[list | None] = mapped_column(jsonb_type())
    error: Mapped[dict | None] = mapped_column(jsonb_type())
    result_summary: Mapped[dict | None] = mapped_column(jsonb_type())
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

