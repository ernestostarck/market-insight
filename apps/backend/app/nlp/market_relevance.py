"""Market relevance (6.16): a single `relevance_score`/`relevance_tier`
that separates *thematic* relevance (is this licitacion about our
niche, regardless of which category won) from *commercial* relevance
(is it still a live opportunity). Pure logic, no DB/network — called
from `EmbeddingsStageExecutor` (app/nlp/semantic.py), the stage that
already has all 3 thematic signals computed.

Commercial relevance is deliberately narrow in this v1: `core.licitacion`
columns for monto_estimado/tipo/es_desierta/es_adjudicada are 100% NULL
in the real dataset today — ChileCompra's listing endpoint
(`LicitacionAPIItem`, app/integrations/chilecompra/models.py) never
returns those fields, and raw_payload isn't persisted either, so there's
nothing to extract them from without extending the ETL (out of scope
here — see docs/07-ai/market-relevance.md). The only real, verifiable
commercial signal today is `fecha_cierre`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.nlp.classification import _RULE_SCORE_SATURATION

# Initial, documented heuristic tiers — real tuning is 6.23 (MLOps &
# Evaluation), same spirit as _RULE_SCORE_SATURATION/_SIMILARITY_THRESHOLD.
_RELEVANCE_TIER_HIGH = 0.66
_RELEVANCE_TIER_MEDIUM = 0.33

# A closed licitacion is no longer an actionable opportunity, but this is a
# market-intelligence platform, not just a bidding assistant — closed
# tenders still carry historical/trend value, so commercial_score is
# discounted, not zeroed.
_CLOSED_COMMERCIAL_MULTIPLIER = 0.5

ALGORITHM_VERSION = "relevance-v1"


@dataclass(frozen=True, slots=True)
class RelevanceResult:
    relevance_score: float
    relevance_tier: str
    thematic_score: float
    commercial_score: float
    explanation: dict


def compute_relevance(
    *, rule_score: float, similarity_score: float, model_score: float, still_open: bool,
) -> RelevanceResult:
    """`thematic_score` takes the max of all 3 raw signals (not just the
    one that won category selection in combine_signals) — for relevance,
    a signal that fired but lost the tie still indicates real topical
    relevance."""
    normalized_rule_score = min(rule_score / _RULE_SCORE_SATURATION, 1.0)
    thematic_score = max(normalized_rule_score, similarity_score, model_score)
    commercial_score = 1.0 if still_open else _CLOSED_COMMERCIAL_MULTIPLIER
    relevance_score = thematic_score * commercial_score

    if relevance_score >= _RELEVANCE_TIER_HIGH:
        relevance_tier = "high"
    elif relevance_score >= _RELEVANCE_TIER_MEDIUM:
        relevance_tier = "medium"
    elif relevance_score > 0.0:
        relevance_tier = "low"
    else:
        relevance_tier = "not_relevant"

    explanation = {
        "algorithm_version": ALGORITHM_VERSION,
        "thematic_score": thematic_score,
        "commercial_score": commercial_score,
        "still_open": still_open,
    }
    return RelevanceResult(relevance_score, relevance_tier, thematic_score, commercial_score, explanation)
