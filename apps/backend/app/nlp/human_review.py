"""Pure logic and validation for human review decisions (Fase 6.17).

Validates consistency of human annotations (category vs subcategory vs relevance),
and computes priority scores for the review queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.nlp.confidence import ReviewReason

_RELEVANCE_WEIGHTS: Mapping[str, float] = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.2,
    "not_relevant": 0.0,
}


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    accepted: bool
    relevant: bool
    category_code: str | None = None
    subcategory_code: str | None = None
    relevance_tier: str | None = None
    reason: str | None = None


def validate_review_decision(
    decision: ReviewDecision,
    *,
    valid_categories: set[str],
    subcategories_by_category: Mapping[str, set[str]],
) -> list[str]:
    """Validates human review decision for logical consistency.

    Returns a list of validation error strings (empty if valid).
    """
    errors: list[str] = []

    if not decision.accepted and not (decision.reason and decision.reason.strip()):
        errors.append("Un motivo (reason) es requerido cuando se modifica o rechaza una predicción.")

    if not decision.relevant:
        if decision.category_code is not None:
            errors.append("Una licitación no relevante (relevant=False) no debe tener category_code.")
        if decision.subcategory_code is not None:
            errors.append("Una licitación no relevante (relevant=False) no debe tener subcategory_code.")
        if decision.relevance_tier is not None and decision.relevance_tier != "not_relevant":
            errors.append(f"relevance_tier debe ser 'not_relevant' cuando relevant=False, recibido: {decision.relevance_tier}")
    else:
        # relevant is True
        if decision.category_code is None:
            errors.append("Una licitación relevante (relevant=True) debe tener category_code asignado.")
        elif decision.category_code not in valid_categories:
            errors.append(f"category_code '{decision.category_code}' no existe en la taxonomía.")
        else:
            # Check subcategory if supplied
            if decision.subcategory_code is not None:
                allowed_subs = subcategories_by_category.get(decision.category_code, set())
                if decision.subcategory_code not in allowed_subs:
                    errors.append(
                        f"subcategory_code '{decision.subcategory_code}' no pertenece a la categoría '{decision.category_code}'."
                    )

    return errors


def compute_review_priority(
    relevance_tier: str | None,
    relevance_score: float | None,
    confidence_score: float,
    reasons: tuple[ReviewReason, ...] | list[ReviewReason],
) -> float:
    """Calculates review priority score (higher means more urgent to review).

    Gives highest priority to high-relevance tenders with high uncertainty (low confidence or conflicting signals).
    """
    tier_weight = _RELEVANCE_WEIGHTS.get(relevance_tier or "", 0.1)
    if relevance_score is not None:
        rel_signal = max(tier_weight, min(relevance_score, 1.0))
    else:
        rel_signal = tier_weight

    uncertainty = max(0.0, 1.0 - confidence_score)

    priority = (rel_signal * 0.6) + (uncertainty * 0.4)

    # Boosts for specific risk factors
    if ReviewReason.CONFLICTING_SIGNALS in reasons:
        priority += 0.25
    if ReviewReason.UNASSIGNED_CATEGORY in reasons:
        priority += 0.20

    return round(priority, 4)
