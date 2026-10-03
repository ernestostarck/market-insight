"""Transport schemas for the NLP pipeline and AI capabilities (Fase 6.1-6.21)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Preprocessing & Rules (Fases 6.1 - 6.7)
# ---------------------------------------------------------------------------

class NLPPreprocessRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)


class NLPPreprocessResponse(BaseModel):
    original_text: str
    normalized_text: str
    language: str


class RuleMatchResponse(BaseModel):
    rule_id: str
    keyword: str
    concept_code: str
    category_code: str
    subcategory_code: str | None
    weight: float
    version: str


class RuleClassificationResponse(BaseModel):
    category_code: str | None
    subcategory_code: str | None
    rule_score: float
    matches: list[RuleMatchResponse]


class TaxonomyConceptResponse(BaseModel):
    code: str
    name: str
    description: str


class TaxonomySubcategoryResponse(BaseModel):
    code: str
    name: str
    description: str
    concepts: list[TaxonomyConceptResponse]


class TaxonomyCategoryResponse(BaseModel):
    code: str
    name: str
    description: str
    subcategories: list[TaxonomySubcategoryResponse]


class TaxonomyResponse(BaseModel):
    version: str
    categories: list[TaxonomyCategoryResponse]


# ---------------------------------------------------------------------------
# 2. Unified Classification (Fases 6.15 & 6.21)
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    text: str | None = Field(None, max_length=100_000, description="Free text or combined tender text")
    title: str | None = Field(None, description="Optional tender title")
    description: str | None = Field(None, description="Optional tender description")
    items: list[str] | None = Field(None, description="Optional tender item names")
    still_open: bool = Field(True, description="Whether tender is currently open")


class ClassifyResponse(BaseModel):
    category_code: str | None
    subcategory_code: str | None
    confidence_score: float
    winning_method: str
    rule_score: float
    similarity_score: float
    model_score: float
    relevance_score: float
    relevance_tier: str
    explanation: dict[str, Any]


class ClassificationItemResponse(BaseModel):
    id: uuid.UUID
    licitacion_id: int
    category_id: int | None
    subcategory_id: int | None
    taxonomy_version: str
    rule_score: float
    similarity_score: float
    model_score: float | None
    confidence_score: float
    relevance_score: float | None
    relevance_tier: str | None
    explanation: dict[str, Any] | None
    created_at: datetime


class ClassificationListResponse(BaseModel):
    total: int
    items: list[ClassificationItemResponse]


# ---------------------------------------------------------------------------
# 3. Semantic Search (Fases 6.9 & 6.21)
# ---------------------------------------------------------------------------

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=100)
    min_similarity: float = Field(0.0, ge=0.0, le=1.0)
    category_code: str | None = None


class SimilarTenderItemResponse(BaseModel):
    licitacion_id: int
    nombre: str | None
    similarity: float
    category_id: int | None
    subcategory_id: int | None


class SemanticSearchResponse(BaseModel):
    query: str
    total: int
    items: list[SimilarTenderItemResponse]


class SimilarTendersResponse(BaseModel):
    source_licitacion_id: int
    total: int
    items: list[SimilarTenderItemResponse]


# ---------------------------------------------------------------------------
# 4. Entity Extraction (Fases 6.11 & 6.21)
# ---------------------------------------------------------------------------

class EntityExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)
    organismo: str | None = None
    region: str | None = None
    comuna: str | None = None
    items: list[str] | None = None


class ExtractedEntityResponse(BaseModel):
    entity_type: str
    value: str
    normalized_value: str | None
    confidence_score: float
    start_offset: int | None
    end_offset: int | None


class EntityExtractionResponse(BaseModel):
    total: int
    entities: list[ExtractedEntityResponse]


# ---------------------------------------------------------------------------
# 5. Product Extraction (Fases 6.12 & 6.21)
# ---------------------------------------------------------------------------

class ProductExtractionRequest(BaseModel):
    item_nombre: str = Field(..., min_length=1, max_length=500)
    item_descripcion: str | None = Field(None, max_length=5000)
    cantidad: float | None = None
    unidad: str | None = None


class MatchedProductConceptResponse(BaseModel):
    concept_code: str
    category_code: str
    subcategory_code: str
    matched_term: str
    start_offset: int
    end_offset: int


class ProductAttributesResponse(BaseModel):
    materiales: list[str]
    dimensiones: str | None
    capacidad: str | None
    caracteristicas_tecnicas: list[str]


class ProductExtractionResponse(BaseModel):
    concepts: list[MatchedProductConceptResponse]
    attributes: ProductAttributesResponse


# ---------------------------------------------------------------------------
# 6. Taxonomy & Categories (Fases 6.5 & 6.21)
# ---------------------------------------------------------------------------

class DomainConceptResponse(BaseModel):
    code: str
    name: str
    description: str


class TaxonomySubcategoryResponse(BaseModel):
    code: str
    name: str
    description: str
    concepts: list[DomainConceptResponse]


class TaxonomyCategoryResponse(BaseModel):
    code: str
    name: str
    description: str
    subcategories: list[TaxonomySubcategoryResponse]


class TaxonomyHierarchyResponse(BaseModel):
    version: str
    categories: list[TaxonomyCategoryResponse]


# ---------------------------------------------------------------------------
# 7. Relevance (Fases 6.16 & 6.21)
# ---------------------------------------------------------------------------

class RelevanceCalculationRequest(BaseModel):
    rule_score: float = Field(..., ge=0.0)
    similarity_score: float = Field(..., ge=0.0)
    model_score: float | None = Field(None, ge=0.0)
    still_open: bool = True
    fecha_cierre: datetime | None = None


class RelevanceCalculationResponse(BaseModel):
    relevance_score: float
    relevance_tier: str
    thematic_score: float
    commercial_score: float
    explanation: dict[str, Any]


# ---------------------------------------------------------------------------
# 8. Human Review (Fases 6.17 & 6.21)
# ---------------------------------------------------------------------------

class ReviewQueueItemResponse(BaseModel):
    classification_id: uuid.UUID
    licitacion_id: int
    licitacion_codigo: str | None = None
    title: str | None
    organismo: str | None = None
    monto_estimado: float | None = None
    item_names: list[str] = Field(default_factory=list)
    confidence_score: float
    confidence_level: str
    relevance_score: float | None
    relevance_tier: str | None
    category_code: str | None
    subcategory_code: str | None
    winning_method: str | None = None
    rule_score: float | None = None
    similarity_score: float | None = None
    model_score: float | None = None
    explanation: dict[str, Any] | None = None
    needs_review: bool
    review_reasons: list[str]
    priority_score: float


class ReviewQueueResponse(BaseModel):
    total: int
    items: list[ReviewQueueItemResponse]


class ReviewAcceptRequest(BaseModel):
    reason: str | None = Field(None, max_length=1000)


class ReviewModifyRequest(BaseModel):
    category_code: str | None = None
    subcategory_code: str | None = None
    relevant: bool = True
    relevance_tier: str | None = None
    reason: str = Field(..., min_length=3, max_length=1000)


class ReviewActionResponse(BaseModel):
    review_id: uuid.UUID
    classification_id: uuid.UUID
    status: str
    message: str


class ReviewStatsResponse(BaseModel):
    stats: dict[str, Any]


# ---------------------------------------------------------------------------
# 9. Models & Versions (Fases 6.14 & 6.21)
# ---------------------------------------------------------------------------

class ModelVersionItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    artifact_uri: str
    state: str
    metrics: dict[str, Any] | None
    created_at: datetime


class DatasetVersionItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    manifest: dict[str, Any] | None
    created_at: datetime


class ModelListResponse(BaseModel):
    models: list[ModelVersionItemResponse]
    datasets: list[DatasetVersionItemResponse]


class ModelPromoteRequest(BaseModel):
    target_status: str = Field(..., description="Target lifecycle state: draft, staging, production, archived")


class ModelPromoteResponse(BaseModel):
    model_id: uuid.UUID
    name: str
    version: str
    previous_status: str
    new_status: str
    demoted_model_id: uuid.UUID | None = None
    demoted_version: str | None = None


class ModelRollbackResponse(BaseModel):
    demoted_model_id: uuid.UUID
    demoted_version: str
    promoted_model_id: uuid.UUID
    promoted_version: str
    status: str


class ModelLineageResponse(BaseModel):
    model_id: uuid.UUID
    name: str
    version: str
    kind: str
    status: str
    artifact_uri: str | None
    dataset_version_id: str | None
    dataset_name: str | None
    dataset_version: str | None
    dataset_record_count: int | None
    hyperparameters: dict[str, Any]
    metrics: dict[str, Any]
    trained_at: str | None
    predictions_count: int


class RetrainRequest(BaseModel):
    dataset_version_id: uuid.UUID | None = None
    random_state: int = 42


class RetrainResponse(BaseModel):
    model_id: uuid.UUID | None = None
    winner_name: str
    model_version: str
    test_f1_macro: float
    status: str
    message: str



# ---------------------------------------------------------------------------
# 10. Jobs (Fases 6.1, 6.20 & 6.21)
# ---------------------------------------------------------------------------

class NLPJobCreate(BaseModel):
    licitacion_id: int = Field(..., gt=0)
    text_hash: str = Field(..., min_length=64, max_length=64)
    taxonomy_version: str = Field(..., min_length=1, max_length=64)
    dictionary_version: str = Field(..., min_length=1, max_length=64)
    model_version: str | None = Field(None, max_length=64)
    embedding_model_version: str | None = Field(None, max_length=64)


class NLPJobAccepted(BaseModel):
    task_id: str
    idempotency_key: str | None = None


class NLPBatchJobCreate(BaseModel):
    jobs: list[NLPJobCreate] = Field(..., min_length=1, max_length=500)


class NLPBatchJobAccepted(BaseModel):
    task_id: str
    total_jobs: int


class NLPJobStatusResponse(BaseModel):
    id: uuid.UUID | None
    celery_task_id: str | None
    idempotency_key: str
    licitacion_id: int
    status: str
    duration_seconds: float | None
    completed_stages: list[str] | None
    pending_stages: list[str] | None
    error: dict[str, Any] | None
    result_summary: dict[str, Any] | None
    retries: int
