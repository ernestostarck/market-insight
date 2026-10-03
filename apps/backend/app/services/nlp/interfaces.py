"""Protocols and interfaces for the NLP Service Layer (Fase 6.18).

Defines formal type contracts (typing.Protocol) for the 11 NLP domain services:
- IPreprocessingService
- IDictionaryService
- ITaxonomyService
- IRuleClassificationService
- IEmbeddingService
- ISemanticSearchService
- IClassificationService
- IEntityExtractionService
- IProductExtractionService
- IRelevanceService
- IReviewService
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

import numpy as np

from app.models.knowledge import Classification, DatasetVersion, Document, Entity, HumanReview, ModelVersion, Product
from app.nlp.confidence import ConfidenceAssessment
from app.nlp.contracts import ModelLifecycleState, ModelLineage, PromotionResult, RollbackResult
from app.nlp.dictionary import DictionaryEntry, DomainTheme
from app.services.nlp.dictionary import DictionaryMatch
from app.nlp.document import TenderDocument
from app.nlp.entities import ExtractedEntity
from app.nlp.human_review_db import ReviewQueueItem
from app.nlp.market_relevance import RelevanceResult
from app.nlp.preprocessing import PreprocessedText
from app.nlp.product_attributes import ProductAttributes
from app.nlp.product_concepts import ProductConceptMatch
from app.nlp.rules import RuleEvaluation
from app.nlp.taxonomy import DomainConcept, TaxonomyCategory, TaxonomySubcategory
from app.repositories.vector_search import SimilarLicitacion


@runtime_checkable
class IPreprocessingService(Protocol):
    """Encapsulates text normalization, unicode cleaning, and chunk generation."""

    def preprocess(self, text: str) -> PreprocessedText:
        ...

    def build_tender_document(
        self, title: str, description: str | None, item_texts: list[str]
    ) -> PreprocessedText:
        ...

    def build_consolidated_document(
        self, licitacion_id: int, title: str, description: str | None, item_texts: list[str]
    ) -> TenderDocument:
        ...

    async def process_and_store_tender(
        self, licitacion_id: int, title: str, description: str | None, item_texts: list[str]
    ) -> Document:
        ...


@runtime_checkable
class IDictionaryService(Protocol):
    """Encapsulates semantic dictionary search, entry resolution, and versioning."""

    def find_matches(self, text: str) -> list[DictionaryMatch]:
        ...

    def get_entry(self, term: str) -> DictionaryEntry | None:
        ...

    def list_terms(self, theme: DomainTheme | None = None) -> list[DictionaryEntry]:
        ...

    def get_version(self) -> str:
        ...


@runtime_checkable
class ITaxonomyService(Protocol):
    """Encapsulates taxonomy hierarchy traversal, code resolution, and integrity checks."""

    def resolve_category(self, code: str) -> TaxonomyCategory | None:
        ...

    def resolve_subcategory(
        self, category_code: str, subcategory_code: str
    ) -> TaxonomySubcategory | None:
        ...

    def locate_concept(
        self, concept_code: str
    ) -> tuple[TaxonomyCategory, TaxonomySubcategory, DomainConcept] | None:
        ...

    def get_hierarchy(self) -> dict[str, Any]:
        ...

    def validate(self) -> list[str]:
        ...


@runtime_checkable
class IRuleClassificationService(Protocol):
    """Encapsulates rule-based deterministic classification and explainability."""

    def evaluate(self, text: str) -> RuleEvaluation:
        ...

    def evaluate_tender(
        self, title: str, description: str | None, items: list[str]
    ) -> RuleEvaluation:
        ...


@runtime_checkable
class IEmbeddingService(Protocol):
    """Encapsulates vector representation generation and similarity computation."""

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        ...

    def compute_similarity(self, vector_a: np.ndarray, vector_b: np.ndarray) -> float:
        ...


@runtime_checkable
class ISemanticSearchService(Protocol):
    """Encapsulates vector search over pgvector for tenders, categories, and concepts."""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
        category_code: str | None = None,
    ) -> list[SimilarLicitacion]:
        ...

    async def find_similar_to_licitacion(
        self, licitacion_id: int, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        ...

    async def search_by_concept(
        self, concept_code: str, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        ...

    async def search_by_category(
        self, category_code: str, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        ...


@runtime_checkable
class IClassificationService(Protocol):
    """Orchestrates hybrid classification combining rules, embeddings, and supervised model."""

    async def classify_text(self, text: str, *, still_open: bool = True) -> dict[str, Any]:
        ...

    async def classify_and_store_tender(
        self,
        licitacion_id: int,
        title: str,
        description: str | None,
        items: list[str],
        *,
        still_open: bool = True,
    ) -> Classification:
        ...


@runtime_checkable
class IEntityExtractionService(Protocol):
    """Encapsulates Named Entity Recognition (NER) for tenders."""

    def extract_entities(
        self,
        text: str,
        *,
        organismo: str | None = None,
        items: list[str] | None = None,
        region: str | None = None,
        comuna: str | None = None,
    ) -> list[ExtractedEntity]:
        ...

    async def extract_and_store(
        self,
        licitacion_id: int,
        text: str,
        *,
        organismo: str | None = None,
        items: list[str] | None = None,
        classification_id: uuid.UUID | None = None,
    ) -> list[Entity]:
        ...


@runtime_checkable
class IProductExtractionService(Protocol):
    """Encapsulates product concept matching and technical attribute extraction."""

    def extract_product_concepts(self, text: str) -> tuple[ProductConceptMatch, ...] | list[ProductConceptMatch]:
        ...

    def extract_product_attributes(self, text: str) -> ProductAttributes:
        ...

    def process_item(
        self,
        licitacion_id: int,
        licitacion_item_id: int,
        item_nombre: str,
        item_descripcion: str | None = None,
        cantidad: float | None = None,
        unidad: str | None = None,
        classification_id: uuid.UUID | None = None,
    ) -> list[Product]:
        ...


@runtime_checkable
class IRelevanceService(Protocol):
    """Encapsulates thematic and commercial market relevance calculation."""

    def compute(
        self,
        rule_score: float,
        similarity_score: float,
        model_score: float | None,
        still_open: bool,
    ) -> RelevanceResult:
        ...

    def assess_tender(
        self,
        rule_score: float,
        similarity_score: float,
        model_score: float | None,
        fecha_cierre: datetime | None,
    ) -> RelevanceResult:
        ...


@runtime_checkable
class IReviewService(Protocol):
    """Encapsulates Human-in-the-Loop review queue, decisions, and dataset synchronization."""

    def evaluate_confidence(
        self,
        confidence_score: float,
        *,
        scores: dict[str, float] | None = None,
        categories: dict[str, str | None] | None = None,
        category_code: str | None = None,
        relevance_tier: str | None = None,
    ) -> ConfidenceAssessment:
        ...

    async def get_queue(
        self, *, threshold: float = 0.65, limit: int = 50, offset: int = 0
    ) -> list[ReviewQueueItem]:
        ...

    async def accept(
        self, classification_id: uuid.UUID, reviewer_id: uuid.UUID, *, reason: str | None = None
    ) -> HumanReview:
        ...

    async def modify(
        self,
        classification_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        *,
        category_code: str | None,
        subcategory_code: str | None,
        relevant: bool,
        relevance_tier: str | None,
        reason: str,
    ) -> HumanReview:
        ...

    async def sync_gold_dataset(self, dataset_version_id: uuid.UUID) -> dict[str, Any]:
        ...


@runtime_checkable
class IModelManagementService(Protocol):
    """Encapsulates model lifecycle, promotion, rollback, and training lineage."""

    async def get_model(self, model_id: uuid.UUID) -> ModelVersion | None:
        ...

    async def get_by_version(self, name: str, version: str) -> ModelVersion | None:
        ...

    async def get_active_model(
        self, kind: str = "classifier", preferred_status: str = "production"
    ) -> ModelVersion | None:
        ...

    async def list_models(
        self, kind: str | None = None, status: str | None = None
    ) -> list[ModelVersion]:
        ...

    async def list_dataset_versions(self) -> list[DatasetVersion]:
        ...

    async def promote_model(
        self, model_id: uuid.UUID, target_status: str | ModelLifecycleState
    ) -> PromotionResult:
        ...

    async def rollback_model(self, kind: str = "classifier") -> RollbackResult:
        ...

    async def get_model_lineage(self, model_id: uuid.UUID) -> ModelLineage | None:
        ...

