"""Application service facade for synchronous deterministic NLP operations."""

from __future__ import annotations

from app.nlp.contracts import NLPJobRequest
from app.nlp.dispatch import NLPJobDispatcher
from app.nlp.preprocessing import TextPreprocessor
from app.nlp.rules import RuleEngine
from app.schemas.nlp import NLPPreprocessResponse, RuleClassificationResponse, RuleMatchResponse


class NLPService:
    def __init__(
        self,
        preprocessor: TextPreprocessor,
        rule_engine: RuleEngine,
        dispatcher: NLPJobDispatcher | None = None,
    ) -> None:
        self._preprocessor = preprocessor
        self._rule_engine = rule_engine
        self._dispatcher = dispatcher

    def submit(self, job: NLPJobRequest) -> str:
        if self._dispatcher is None:
            raise RuntimeError("NLP worker dispatcher is not configured")
        return self._dispatcher.dispatch(job)

    def preprocess(self, text: str) -> NLPPreprocessResponse:
        result = self._preprocessor.preprocess(text)
        return NLPPreprocessResponse(
            original_text=result.original_text,
            normalized_text=result.normalized_text,
            language=result.language,
        )

    def classify_by_rules(self, text: str) -> RuleClassificationResponse:
        evaluation = self._rule_engine.evaluate(
            self._preprocessor.preprocess(text).normalized_text
        )
        return RuleClassificationResponse(
            category_code=evaluation.category_code,
            subcategory_code=evaluation.subcategory_code,
            rule_score=evaluation.score,
            matches=[
                RuleMatchResponse(
                    rule_id=match.rule_id,
                    keyword=match.keyword,
                    concept_code=match.concept_code,
                    category_code=match.category_code,
                    subcategory_code=match.subcategory_code,
                    weight=match.weight,
                    version=match.version,
                )
                for match in evaluation.matches
            ],
        )
