"""Confidence evaluation and uncertainty detection for NLP classifications (Fase 6.17).

Defines the confidence calculation strategy, evaluation thresholds, and heuristic
checks (conflicting signals, low confidence, unassigned categories, and borderline relevance)
to identify predictions that warrant human review.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.65
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.80
DEFAULT_CONFLICT_MARGIN = 0.15


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    CONFLICTING_SIGNALS = "conflicting_signals"
    UNASSIGNED_CATEGORY = "unassigned_category"
    BORDERLINE_RELEVANCE = "borderline_relevance"


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    level: ConfidenceLevel
    confidence_score: float
    needs_review: bool
    reasons: tuple[ReviewReason, ...]
    conflict_details: str | None = None


def detect_conflicting_signals(
    scores: dict[str, float] | None,
    categories: dict[str, str | None] | None,
    *,
    margin: float = DEFAULT_CONFLICT_MARGIN,
) -> tuple[bool, str | None]:
    """Detects whether two signals produced different categories with scores within margin.

    Returns (has_conflict, conflict_description).
    """
    if not scores or not categories:
        return False, None

    # Filter to signals that actively predicted a category
    active = [
        (method, categories[method], scores.get(method, 0.0))
        for method in categories
        if categories[method] is not None and method in scores
    ]

    if len(active) < 2:
        return False, None

    # Sort descending by score
    active.sort(key=lambda item: item[2], reverse=True)

    top_method, top_cat, top_score = active[0]
    for method, cat, score in active[1:]:
        if cat != top_cat and (top_score - score) <= margin:
            return True, f"Conflict: {top_method} ({top_cat}, {top_score:.3f}) vs {method} ({cat}, {score:.3f}) (margin <= {margin})"

    return False, None


def evaluate_prediction_confidence(
    confidence_score: float,
    *,
    scores: dict[str, float] | None = None,
    categories: dict[str, str | None] | None = None,
    category_code: str | None = None,
    relevance_tier: str | None = None,
    low_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    conflict_margin: float = DEFAULT_CONFLICT_MARGIN,
) -> ConfidenceAssessment:
    """Evaluates the confidence level of a classification prediction.

    - HIGH: confidence_score >= high_threshold, category assigned, no conflicts.
    - MEDIUM: low_threshold <= confidence_score < high_threshold, category assigned, no conflicts.
    - LOW: confidence_score < low_threshold OR conflicting signals OR no category with relevant tender.
    """
    reasons: list[ReviewReason] = []

    # 1. Check for conflicting signals between rule / model / semantic
    has_conflict, conflict_desc = detect_conflicting_signals(scores, categories, margin=conflict_margin)
    if has_conflict:
        reasons.append(ReviewReason.CONFLICTING_SIGNALS)

    # 2. Check for low confidence score
    if confidence_score < low_threshold:
        reasons.append(ReviewReason.LOW_CONFIDENCE)

    # 3. Check for unassigned category on tenders that showed some relevance
    is_relevant_tier = relevance_tier in ("high", "medium")
    if category_code is None:
        if is_relevant_tier:
            reasons.append(ReviewReason.UNASSIGNED_CATEGORY)
        elif confidence_score > 0.0:
            reasons.append(ReviewReason.LOW_CONFIDENCE)

    # 4. Check for borderline relevance with moderate confidence
    if is_relevant_tier and confidence_score < high_threshold and ReviewReason.LOW_CONFIDENCE not in reasons:
        reasons.append(ReviewReason.BORDERLINE_RELEVANCE)

    needs_review = len(reasons) > 0

    if has_conflict or confidence_score < low_threshold or (category_code is None and is_relevant_tier):
        level = ConfidenceLevel.LOW
    elif confidence_score >= high_threshold and not has_conflict:
        level = ConfidenceLevel.HIGH
    else:
        level = ConfidenceLevel.MEDIUM

    return ConfidenceAssessment(
        level=level,
        confidence_score=confidence_score,
        needs_review=needs_review,
        reasons=tuple(reasons),
        conflict_details=conflict_desc,
    )
