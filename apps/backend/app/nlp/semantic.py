"""EMBEDDINGS stage executor: encode the document, persist the vector to
`knowledge.embeddings`, run the persisted supervised classifier (6.14) if
one is loaded, and combine rule/semantic/model signals into the
`knowledge.classifications` row that CLASSIFICATION left behind (the
pipeline order is classification -> embeddings -> knowledge — see
docs/07-ai/architecture.md). 6.15 adds the model signal and the explicit
combination policy (app/nlp/hybrid_classification.py) — before that, the
policy was implicit and ad-hoc: rules always won the category if they
matched anything, however weak, over a possibly much more confident
semantic score. 6.16 adds `relevance_score`/`relevance_tier`
(app/nlp/market_relevance.py) — a market-relevance concept distinct
from `confidence_score` (which measures confidence in the winning
category, not whether the tender is a worthwhile opportunity).

Same Core (Connection + text()) style as ClassificationStageExecutor
(app/nlp/classification.py) and CoreLicitacionLoader.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Callable

import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.ml.embeddings import EmbeddingService
from app.nlp.hybrid_classification import SignalResult, combine_signals
from app.nlp.market_relevance import compute_relevance
from app.nlp.observability.metrics import (
    record_nlp_classification,
    record_nlp_embedding_failure,
)
from app.nlp.stages import StageContext
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_db import resolve_category, resolve_subcategory
from app.nlp.taxonomy_vectors import ConceptVector, build_concept_vectors

logger = logging.getLogger(__name__)

# Initial, documented threshold — a concept must be at least this similar to
# the document to count as a semantic match. Real tuning is 6.23 (MLOps &
# Evaluation), same spirit as _RULE_SCORE_SATURATION in classification.py.
_SIMILARITY_THRESHOLD = 0.5

# Label the supervised model (6.14) uses for "no category" — see
# app/nlp/classifier_training.py::fetch_training_rows / compute_class_distribution.
_MODEL_NOT_RELEVANT_LABEL = "not_relevant"


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _to_pgvector_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector.tolist()) + "]"


class EmbeddingsStageExecutor:
    """Concept/category embeddings are computed once in memory from the
    taxonomy (name + description) and cached for the executor's lifetime —
    they're few (~15 nodes today) and fully derived from taxonomy.json + the
    model, so persisting them is unnecessary churn (confirmed with the user
    during 6.8 planning)."""

    def __init__(
        self,
        connection_factory: Callable[[], Connection],
        embedding_service: EmbeddingService,
        taxonomy: Taxonomy | None = None,
        model_name: str = EmbeddingService.MODEL_NAME,
        model_version: str = "v1",
        classifier=None,
        classifier_model_version_id: uuid.UUID | None = None,
        classifier_dataset_version_id: uuid.UUID | None = None,
    ) -> None:
        """`classifier` is a fitted sklearn Pipeline (6.14) the caller
        loaded once from MinIO via `classifier_training_db.
        latest_production_or_staging_classifier` + `joblib.load` — `None`
        means no classifier has been trained yet, in which case the
        pipeline still works with rules+semantic only, same as before
        6.15. `classifier_model_version_id`/`classifier_dataset_version_id`
        come along with it (the ModelVersion row's own id, and the Gold
        Dataset version recorded in its `parameters`) so every row this
        executor writes stays traceable to exactly what produced it."""
        self._connection_factory = connection_factory
        self._embedding_service = embedding_service
        self._taxonomy = taxonomy or load_initial_taxonomy()
        self._model_name = model_name
        self._model_version = model_version
        self._concept_vectors = build_concept_vectors(self._taxonomy, self._embedding_service)
        self._classifier = classifier
        self._classifier_model_version_id = classifier_model_version_id
        self._classifier_dataset_version_id = classifier_dataset_version_id

    def run(self, context: StageContext) -> bool:
        connection = self._connection_factory()
        try:
            document = connection.execute(
                text(
                    "SELECT normalized_text FROM knowledge.documents "
                    "WHERE licitacion_id = :licitacion_id AND content_hash = :content_hash"
                ),
                {"licitacion_id": context.licitacion_id, "content_hash": context.text_hash},
            ).first()
            if document is None:
                logger.warning(
                    "No preprocessed document for licitacion_id=%s content_hash=%s",
                    context.licitacion_id, context.text_hash,
                )
                return False

            try:
                vector = self._embedding_service.encode([document[0]])[0]
            except Exception:
                record_nlp_embedding_failure(self._model_name)
                raise
            model_version_id = self._resolve_model_version(connection)

            connection.execute(
                text(
                    "INSERT INTO knowledge.embeddings "
                    "(id, licitacion_id, model_version_id, content_hash, text, vector) "
                    "VALUES (:id, :licitacion_id, :model_version_id, :content_hash, :text, :vector)"
                ),
                {
                    "id": uuid.uuid4(), "licitacion_id": context.licitacion_id,
                    "model_version_id": model_version_id, "content_hash": context.text_hash,
                    "text": document[0], "vector": _to_pgvector_literal(vector),
                },
            )

            semantic_score, best_node = self._best_match(vector)
            model_category_code, model_score = self._classify(document[0])
            self._update_or_create_classification(
                connection, context, semantic_score, best_node, model_category_code, model_score,
            )

            connection.commit()
            return True
        except Exception:
            logger.exception("embeddings stage failed for licitacion_id=%s", context.licitacion_id)
            connection.rollback()
            return False
        finally:
            connection.close()

    def _best_match(self, vector: np.ndarray) -> tuple[float, ConceptVector | None]:
        if not self._concept_vectors:
            return 0.0, None
        score, node = max(
            ((cosine_similarity(vector, candidate.vector), candidate) for candidate in self._concept_vectors),
            key=lambda item: item[0],
        )
        return score, node

    def _classify(self, normalized_text: str) -> tuple[str | None, float]:
        """Runs the persisted classifier (6.14) if one was loaded.
        Returns (predicted_category_code_or_None, probability_of_that_class)
        — the model's own training labels are category codes or
        "not_relevant" (app/nlp/classifier_training.py), so "not_relevant"
        maps to no category, same convention as rules/semantic having no
        match."""
        if self._classifier is None:
            return None, 0.0
        predicted_label = self._classifier.predict([normalized_text])[0]
        probabilities = self._classifier.predict_proba([normalized_text])[0]
        score = float(max(probabilities))
        if predicted_label == _MODEL_NOT_RELEVANT_LABEL:
            return None, score
        return predicted_label, score

    def _resolve_model_version(self, connection: Connection) -> uuid.UUID:
        row = connection.execute(
            text("SELECT id FROM knowledge.model_versions WHERE name = :name AND version = :version"),
            {"name": self._model_name, "version": self._model_version},
        ).first()
        if row is not None:
            return row[0]
        model_version_id = uuid.uuid4()
        connection.execute(
            text(
                "INSERT INTO knowledge.model_versions (id, name, version, kind, status) "
                "VALUES (:id, :name, :version, 'embedding', 'production')"
            ),
            {"id": model_version_id, "name": self._model_name, "version": self._model_version},
        )
        return model_version_id

    def _update_or_create_classification(
        self,
        connection: Connection,
        context: StageContext,
        semantic_score: float,
        best_node: ConceptVector | None,
        model_category_code: str | None,
        model_score: float,
    ) -> None:
        existing = connection.execute(
            text(
                "SELECT cl.id, cl.rule_score, cl.explanation, cat.code AS category_code, sub.code AS subcategory_code "
                "FROM knowledge.classifications cl "
                "LEFT JOIN knowledge.categories cat ON cat.id = cl.category_id "
                "LEFT JOIN knowledge.subcategories sub ON sub.id = cl.subcategory_id "
                "WHERE cl.licitacion_id = :licitacion_id AND cl.taxonomy_version = :taxonomy_version "
                "ORDER BY cl.created_at DESC LIMIT 1"
            ),
            {"licitacion_id": context.licitacion_id, "taxonomy_version": self._taxonomy.version},
        ).first()

        rule_signal = SignalResult(
            "rule", existing.category_code if existing else None, existing.subcategory_code if existing else None,
            (existing.rule_score if existing and existing.rule_score is not None else 0.0),
        )
        semantic_match = best_node is not None and semantic_score >= _SIMILARITY_THRESHOLD
        semantic_signal = SignalResult(
            "semantic", best_node.category_code if semantic_match else None,
            best_node.subcategory_code if semantic_match else None, semantic_score,
        )
        model_signal = SignalResult("model", model_category_code, None, model_score)

        result = combine_signals((rule_signal, semantic_signal, model_signal))
        record_nlp_classification(
            category_code=result.category_code or "not_relevant",
            method=result.winning_method or "none",
            confidence=result.confidence_score,
        )

        still_open = connection.execute(
            text("SELECT fecha_cierre IS NULL OR fecha_cierre >= now() FROM core.licitacion WHERE id = :licitacion_id"),
            {"licitacion_id": context.licitacion_id},
        ).scalar()
        relevance = compute_relevance(
            rule_score=rule_signal.score, similarity_score=semantic_score,
            model_score=model_score, still_open=bool(still_open),
        )

        category_id = subcategory_id = None
        if result.category_code is not None:
            category_id = resolve_category(connection, self._taxonomy, result.category_code)
            if result.subcategory_code is not None:
                subcategory_id = resolve_subcategory(
                    connection, self._taxonomy, category_id, result.category_code, result.subcategory_code,
                )

        existing_explanation = (existing.explanation if existing else None) or {}
        explanation = {**existing_explanation, "hybrid": result.explanation, "relevance": relevance.explanation}

        if existing is not None:
            connection.execute(
                text(
                    "UPDATE knowledge.classifications SET category_id = :category_id, "
                    "subcategory_id = :subcategory_id, similarity_score = :similarity_score, "
                    "model_score = :model_score, confidence_score = :confidence_score, "
                    "relevance_score = :relevance_score, relevance_tier = :relevance_tier, "
                    "model_version_id = :model_version_id, dataset_version_id = :dataset_version_id, "
                    "explanation = :explanation WHERE id = :id"
                ),
                {
                    "category_id": category_id, "subcategory_id": subcategory_id,
                    "similarity_score": semantic_score, "model_score": model_score,
                    "confidence_score": result.confidence_score,
                    "relevance_score": relevance.relevance_score, "relevance_tier": relevance.relevance_tier,
                    "model_version_id": self._classifier_model_version_id,
                    "dataset_version_id": self._classifier_dataset_version_id,
                    "explanation": json.dumps(explanation), "id": existing.id,
                },
            )
            return

        connection.execute(
            text(
                "INSERT INTO knowledge.classifications "
                "(id, licitacion_id, category_id, subcategory_id, taxonomy_version, similarity_score, "
                "model_score, confidence_score, relevance_score, relevance_tier, "
                "model_version_id, dataset_version_id, explanation) "
                "VALUES (:id, :licitacion_id, :category_id, :subcategory_id, :taxonomy_version, "
                ":similarity_score, :model_score, :confidence_score, :relevance_score, :relevance_tier, "
                ":model_version_id, :dataset_version_id, :explanation)"
            ),
            {
                "id": uuid.uuid4(), "licitacion_id": context.licitacion_id,
                "category_id": category_id, "subcategory_id": subcategory_id,
                "taxonomy_version": self._taxonomy.version,
                "similarity_score": semantic_score, "model_score": model_score,
                "confidence_score": result.confidence_score,
                "relevance_score": relevance.relevance_score, "relevance_tier": relevance.relevance_tier,
                "model_version_id": self._classifier_model_version_id,
                "dataset_version_id": self._classifier_dataset_version_id,
                "explanation": json.dumps(explanation),
            },
        )
