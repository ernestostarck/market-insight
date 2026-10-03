"""Market relevance application service (Fase 6.18)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.nlp.market_relevance import RelevanceResult, compute_relevance


class RelevanceService:
    def compute(
        self,
        rule_score: float,
        similarity_score: float,
        model_score: float | None,
        still_open: bool,
    ) -> RelevanceResult:
        return compute_relevance(
            rule_score=rule_score,
            similarity_score=similarity_score,
            model_score=model_score if model_score is not None else 0.0,
            still_open=still_open,
        )

    def assess_tender(
        self,
        rule_score: float,
        similarity_score: float,
        model_score: float | None,
        fecha_cierre: datetime | None,
    ) -> RelevanceResult:
        still_open = fecha_cierre is None or fecha_cierre >= datetime.now(timezone.utc)
        return self.compute(
            rule_score=rule_score,
            similarity_score=similarity_score,
            model_score=model_score,
            still_open=still_open,
        )
