"""Human review application service (Fase 6.18)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.engine import Connection

from app.nlp.confidence import (
    ConfidenceAssessment,
    DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    evaluate_prediction_confidence,
)
from app.nlp.human_review import ReviewDecision, validate_review_decision
from app.nlp.human_review_db import (
    ReviewQueueItem,
    fetch_review_queue,
    get_review_statistics,
    incorporate_feedback_to_gold_dataset,
    record_human_review,
)
from app.services.nlp.taxonomy import TaxonomyService


class ReviewService:
    def __init__(
        self,
        taxonomy_service: TaxonomyService | None = None,
    ) -> None:
        self._taxonomy = taxonomy_service or TaxonomyService()

    def evaluate_confidence(
        self,
        confidence_score: float,
        *,
        scores: dict[str, float] | None = None,
        categories: dict[str, str | None] | None = None,
        category_code: str | None = None,
        relevance_tier: str | None = None,
    ) -> ConfidenceAssessment:
        return evaluate_prediction_confidence(
            confidence_score,
            scores=scores,
            categories=categories,
            category_code=category_code,
            relevance_tier=relevance_tier,
        )

    def get_queue(
        self,
        connection: Connection,
        *,
        threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
        limit: int = 50,
        offset: int = 0,
        only_unreviewed: bool = True,
    ) -> list[ReviewQueueItem]:
        return fetch_review_queue(
            connection,
            low_threshold=threshold,
            limit=limit,
            offset=offset,
            only_unreviewed=only_unreviewed,
        )

    def accept(
        self,
        connection: Connection,
        classification_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        *,
        category_id: int | None = None,
        subcategory_id: int | None = None,
        relevant: bool = True,
        relevance_tier: str | None = None,
        reason: str | None = None,
    ) -> uuid.UUID:
        return record_human_review(
            connection,
            classification_id=classification_id,
            reviewer_id=reviewer_id,
            accepted=True,
            relevant=relevant,
            category_id=category_id,
            subcategory_id=subcategory_id,
            relevance_tier=relevance_tier,
            reason=reason or "Predicción aceptada por revisor humano.",
        )

    def modify(
        self,
        connection: Connection,
        classification_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        *,
        category_code: str | None,
        subcategory_code: str | None,
        relevant: bool,
        relevance_tier: str | None,
        reason: str,
        category_id: int | None = None,
        subcategory_id: int | None = None,
    ) -> uuid.UUID:
        valid_cats = {c.code for c in self._taxonomy._taxonomy.categories}
        sub_by_cat = {
            c.code: {s.code for s in c.subcategories}
            for c in self._taxonomy._taxonomy.categories
        }
        decision = ReviewDecision(
            accepted=False,
            relevant=relevant,
            category_code=category_code,
            subcategory_code=subcategory_code,
            relevance_tier=relevance_tier,
            reason=reason,
        )
        errors = validate_review_decision(
            decision, valid_categories=valid_cats, subcategories_by_category=sub_by_cat
        )
        if errors:
            raise ValueError(f"Error de validación en revisión humana: {'; '.join(errors)}")

        return record_human_review(
            connection,
            classification_id=classification_id,
            reviewer_id=reviewer_id,
            accepted=False,
            relevant=relevant,
            category_id=category_id,
            subcategory_id=subcategory_id,
            relevance_tier=relevance_tier,
            reason=reason,
        )

    def sync_gold_dataset(
        self, connection: Connection, dataset_version_id: uuid.UUID
    ) -> dict[str, Any]:
        return incorporate_feedback_to_gold_dataset(
            connection, dataset_version_id=dataset_version_id
        )

    def get_stats(self, connection: Connection) -> dict[str, Any]:
        return get_review_statistics(connection)
