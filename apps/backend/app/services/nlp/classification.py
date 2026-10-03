"""Unified hybrid classification application service (Fase 6.18)."""

from __future__ import annotations

import uuid
from typing import Any

from app.models.knowledge import Classification
from app.nlp.hybrid_classification import SignalResult, combine_signals
from app.nlp.semantic import _SIMILARITY_THRESHOLD, cosine_similarity
from app.nlp.taxonomy_vectors import build_concept_vectors


def _find_best_matching_concept(vector, concept_vectors):
    if not concept_vectors:
        return None, 0.0
    score, node = max(
        ((cosine_similarity(vector, candidate.vector), candidate) for candidate in concept_vectors),
        key=lambda item: item[0],
    )
    return node, score
from app.repositories.knowledge import ClassificationRepository
from app.services.nlp.embeddings import EmbeddingService
from app.services.nlp.preprocessing import PreprocessingService
from app.services.nlp.relevance import RelevanceService
from app.services.nlp.rules import RuleClassificationService
from app.services.nlp.taxonomy import TaxonomyService


class ClassificationService:
    def __init__(
        self,
        preprocessing_service: PreprocessingService,
        rule_service: RuleClassificationService,
        embedding_service: EmbeddingService,
        taxonomy_service: TaxonomyService,
        relevance_service: RelevanceService,
        classifier: Any | None = None,
        classification_repository: ClassificationRepository | None = None,
        classifier_model_version_id: uuid.UUID | None = None,
        classifier_dataset_version_id: uuid.UUID | None = None,
        concept_vectors: tuple[Any, ...] | None = None,
    ) -> None:
        self._preprocessor = preprocessing_service
        self._rules = rule_service
        self._embeddings = embedding_service
        self._taxonomy = taxonomy_service
        self._relevance = relevance_service
        self._classifier = classifier
        self._repo = classification_repository
        self._model_version_id = classifier_model_version_id
        self._dataset_version_id = classifier_dataset_version_id

        # Concept vectors for semantic matching
        if concept_vectors is not None:
            self._concept_vectors = concept_vectors
        else:
            self._concept_vectors = build_concept_vectors(
                self._taxonomy._taxonomy, self._embeddings._base
            )

    async def classify_text(self, text: str, *, still_open: bool = True) -> dict[str, Any]:
        normalized = self._preprocessor.preprocess(text).normalized_text

        # 1. Rule signal
        rule_eval = self._rules.evaluate(normalized)
        rule_signal = SignalResult(
            method="rule",
            category_code=rule_eval.category_code,
            subcategory_code=rule_eval.subcategory_code,
            score=rule_eval.score,
        )

        # 2. Semantic signal
        doc_vector = self._embeddings.encode([normalized])[0]
        best_node, semantic_score = _find_best_matching_concept(doc_vector, self._concept_vectors)
        semantic_match = best_node is not None and semantic_score >= _SIMILARITY_THRESHOLD
        semantic_signal = SignalResult(
            method="semantic",
            category_code=best_node.category_code if semantic_match else None,
            subcategory_code=best_node.subcategory_code if semantic_match else None,
            score=semantic_score,
        )

        # 3. Supervised model signal
        model_category: str | None = None
        model_score = 0.0
        if self._classifier is not None:
            pred = self._classifier.predict([normalized])[0]
            if pred != "not_relevant":
                model_category = pred
            if hasattr(self._classifier, "predict_proba"):
                idx = list(self._classifier.classes_).index(pred)
                model_score = float(self._classifier.predict_proba([normalized])[0][idx])
            else:
                model_score = 1.0 if model_category else 0.0
        model_signal = SignalResult(
            method="model",
            category_code=model_category,
            subcategory_code=None,
            score=model_score,
        )

        # 4. Combine signals
        hybrid = combine_signals((rule_signal, semantic_signal, model_signal))

        # 5. Relevance computation
        relevance = self._relevance.compute(
            rule_score=rule_signal.score,
            similarity_score=semantic_score,
            model_score=model_score,
            still_open=still_open,
        )

        explanation = {
            "matched_rules": [m.rule_id for m in rule_eval.matches],
            "hybrid": hybrid.explanation,
            "relevance": relevance.explanation,
        }

        return {
            "category_code": hybrid.category_code,
            "subcategory_code": hybrid.subcategory_code,
            "confidence_score": hybrid.confidence_score,
            "winning_method": hybrid.winning_method,
            "rule_score": rule_signal.score,
            "similarity_score": semantic_score,
            "model_score": model_score,
            "relevance_score": relevance.relevance_score,
            "relevance_tier": relevance.relevance_tier,
            "explanation": explanation,
        }

    async def classify_and_store_tender(
        self,
        licitacion_id: int,
        title: str,
        description: str | None,
        items: list[str],
        *,
        still_open: bool = True,
    ) -> Classification:
        doc = self._preprocessor.build_tender_document(
            title=title, description=description, item_texts=items
        )
        res = await self.classify_text(doc.normalized_text, still_open=still_open)

        classification_id = uuid.uuid4()
        cl = Classification(
            id=classification_id,
            licitacion_id=licitacion_id,
            category_id=None,  # resolved via DB or caller
            subcategory_id=None,
            taxonomy_version=self._taxonomy.get_version(),
            rule_score=res["rule_score"],
            similarity_score=res["similarity_score"],
            model_score=res["model_score"],
            confidence_score=res["confidence_score"],
            relevance_score=res["relevance_score"],
            relevance_tier=res["relevance_tier"],
            model_version_id=self._model_version_id,
            dataset_version_id=self._dataset_version_id,
            explanation=res["explanation"],
        )

        if self._repo is not None:
            cl = await self._repo.create(cl)

        return cl
