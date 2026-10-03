"""CLASSIFICATION stage executor: rule-based match -> persisted `knowledge.classifications`.

Same Core (Connection + text()) style as CoreLicitacionLoader
(app/etl/loading/core_schema.py) — the established pattern for writing to
Postgres from a synchronous Celery task (app/db/session.py is async-only,
built for FastAPI request handlers, not the worker).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.apparel_rules import build_apparel_ruleset
from app.nlp.dictionary import DomainDictionary, load_initial_dictionary
from app.nlp.rules import RuleEngine, RuleMatch, build_ruleset
from app.nlp.stages import StageContext
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_db import resolve_category, resolve_subcategory

logger = logging.getLogger(__name__)

# Initial, documented heuristic: 3+ of accumulated rule weight saturates
# confidence to 1.0. Real tuning is 6.23 (MLOps & Evaluation) — this exists
# so confidence_score (NOT NULL) has a bounded, defensible value from day one.
_RULE_SCORE_SATURATION = 3.0


class ClassificationStageExecutor:
    """Runs the deterministic rule engine against a licitacion's document
    and persists the result to `knowledge.classifications`."""

    def __init__(
        self,
        connection_factory: Callable[[], Connection],
        dictionary: DomainDictionary | None = None,
        taxonomy: Taxonomy | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._taxonomy = taxonomy or load_initial_taxonomy()
        self._dictionary = dictionary or load_initial_dictionary()
        self._engine = RuleEngine(
            build_ruleset(self._dictionary, self._taxonomy) + build_apparel_ruleset()
        )

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

            evaluation = self._engine.evaluate(document[0])

            category_id: int | None = None
            subcategory_id: int | None = None
            if evaluation.category_code is not None:
                category_id = resolve_category(connection, self._taxonomy, evaluation.category_code)
                if evaluation.subcategory_code is not None:
                    subcategory_id = resolve_subcategory(
                        connection, self._taxonomy, category_id, evaluation.category_code, evaluation.subcategory_code,
                    )
                for match in evaluation.matches:
                    self._resolve_rule(connection, match)

            confidence_score = min(evaluation.score / _RULE_SCORE_SATURATION, 1.0)
            explanation = {
                "matched_rules": [
                    {
                        "rule_id": match.rule_id, "concept_code": match.concept_code,
                        "keyword": match.keyword, "weight": match.weight,
                    }
                    for match in evaluation.matches
                ],
            }
            connection.execute(
                text(
                    "INSERT INTO knowledge.classifications "
                    "(id, licitacion_id, category_id, subcategory_id, taxonomy_version, "
                    "rule_score, confidence_score, explanation) "
                    "VALUES (:id, :licitacion_id, :category_id, :subcategory_id, :taxonomy_version, "
                    ":rule_score, :confidence_score, :explanation)"
                ),
                {
                    "id": uuid.uuid4(), "licitacion_id": context.licitacion_id,
                    "category_id": category_id, "subcategory_id": subcategory_id,
                    "taxonomy_version": self._taxonomy.version, "rule_score": evaluation.score,
                    "confidence_score": confidence_score, "explanation": json.dumps(explanation),
                },
            )
            connection.commit()
            return True
        except Exception:
            logger.exception("classification stage failed for licitacion_id=%s", context.licitacion_id)
            connection.rollback()
            return False
        finally:
            connection.close()

    def _resolve_rule(self, connection: Connection, match: RuleMatch) -> None:
        row = connection.execute(
            text("SELECT id FROM knowledge.rules WHERE code = :code AND version = :version"),
            {"code": match.rule_id, "version": match.version},
        ).first()
        if row is not None:
            return
        connection.execute(
            text(
                "INSERT INTO knowledge.rules "
                "(id, code, version, rule_type, pattern, category_id, subcategory_id, weight, active) "
                "VALUES (:id, :code, :version, :rule_type, :pattern, "
                "(SELECT id FROM knowledge.categories WHERE code = :category_code AND taxonomy_version = :taxonomy_version), "
                "(SELECT id FROM knowledge.subcategories WHERE code = :subcategory_code AND taxonomy_version = :taxonomy_version), "
                ":weight, true)"
            ),
            {
                "id": uuid.uuid4(), "code": match.rule_id, "version": match.version,
                "rule_type": "keyword", "pattern": match.keyword,
                "category_code": match.category_code, "subcategory_code": match.subcategory_code,
                "taxonomy_version": self._taxonomy.version, "weight": match.weight,
            },
        )
