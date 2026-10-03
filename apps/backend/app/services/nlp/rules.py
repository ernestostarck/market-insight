"""Rule-based classification application service (Fase 6.18)."""

from __future__ import annotations

from app.nlp.apparel_rules import build_apparel_ruleset
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.preprocessing import TextPreprocessor
from app.nlp.rules import RuleEngine, RuleEvaluation, build_ruleset
from app.nlp.taxonomy import load_initial_taxonomy


class RuleClassificationService:
    def __init__(
        self,
        rule_engine: RuleEngine | None = None,
        preprocessor: TextPreprocessor | None = None,
    ) -> None:
        self._preprocessor = preprocessor or TextPreprocessor()
        if rule_engine is None:
            tax = load_initial_taxonomy()
            dic = load_initial_dictionary()
            self._rule_engine = RuleEngine(build_ruleset(dic, tax) + build_apparel_ruleset())
        else:
            self._rule_engine = rule_engine

    def evaluate(self, text: str) -> RuleEvaluation:
        normalized = self._preprocessor.preprocess(text).normalized_text
        return self._rule_engine.evaluate(normalized)

    def evaluate_tender(
        self, title: str, description: str | None, items: list[str]
    ) -> RuleEvaluation:
        doc = self._preprocessor.build_tender_document(
            title=title, description=description, item_texts=items
        )
        return self._rule_engine.evaluate(doc.normalized_text)
