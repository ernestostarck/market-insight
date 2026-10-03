"""Explicit combination policy for the 3 classification signals (6.15):
rules (6.7), semantic similarity (6.8), and the supervised model (6.14).

Before 6.15 the combination was implicit and ad-hoc
(`EmbeddingsStageExecutor._update_or_create_classification`, pre-6.15:
rules always won the category if they matched anything at all, no matter
how weak, over a possibly much more confident semantic score). This
replaces that with one explicit, documented rule.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tie-break order when two signals report the exact same score (rare in
# practice — scores are floats — but must be deterministic). Rules first:
# a keyword match is a fully deterministic, auditable decision. The model
# is second: it was itself selected and evaluated (6.14), more principled
# than a single cosine-similarity threshold. Semantic last: the fuzziest
# of the three, most prone to false positives on an under-populated
# taxonomy (see docs/07-ai/hybrid-classification-pipeline.md).
_PRECEDENCE = {"rule": 0, "model": 1, "semantic": 2}


@dataclass(frozen=True, slots=True)
class SignalResult:
    method: str  # "rule" | "semantic" | "model"
    category_code: str | None
    subcategory_code: str | None
    score: float


@dataclass(frozen=True, slots=True)
class HybridResult:
    category_code: str | None
    subcategory_code: str | None
    confidence_score: float
    winning_method: str | None
    explanation: dict


def combine_signals(signals: tuple[SignalResult, ...]) -> HybridResult:
    """v1 policy, documented and simple on purpose (real tuning is 6.23,
    same spirit as every other heuristic threshold in this project): among
    the signals that actually produced a category, the highest score
    wins. A signal with no category (no rule matched, similarity below
    threshold, etc.) never competes — it contributes nothing but its raw
    score to `explanation`."""
    candidates = [signal for signal in signals if signal.category_code is not None]
    explanation = {
        "scores": {signal.method: signal.score for signal in signals},
        "categories": {
            signal.method: signal.category_code for signal in signals if signal.category_code is not None
        },
    }

    if not candidates:
        best_score = max((signal.score for signal in signals), default=0.0)
        return HybridResult(
            category_code=None, subcategory_code=None, confidence_score=best_score,
            winning_method=None, explanation=explanation,
        )

    winner = max(candidates, key=lambda signal: (signal.score, -_PRECEDENCE[signal.method]))
    explanation["winning_method"] = winner.method
    return HybridResult(
        category_code=winner.category_code, subcategory_code=winner.subcategory_code,
        confidence_score=winner.score, winning_method=winner.method, explanation=explanation,
    )
