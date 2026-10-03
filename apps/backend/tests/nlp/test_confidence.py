from app.nlp.confidence import (
    ConfidenceLevel,
    ReviewReason,
    detect_conflicting_signals,
    evaluate_prediction_confidence,
)


def test_detect_conflicting_signals_identifies_close_divergent_categories() -> None:
    scores = {"rule": 0.70, "model": 0.68, "semantic": 0.40}
    categories = {"rule": "health", "model": "construction", "semantic": "health"}

    has_conflict, desc = detect_conflicting_signals(scores, categories, margin=0.15)
    assert has_conflict is True
    assert desc is not None
    assert "health" in desc and "construction" in desc


def test_detect_conflicting_signals_no_conflict_when_categories_agree() -> None:
    scores = {"rule": 0.75, "model": 0.72}
    categories = {"rule": "health", "model": "health"}

    has_conflict, desc = detect_conflicting_signals(scores, categories, margin=0.15)
    assert has_conflict is False
    assert desc is None


def test_detect_conflicting_signals_no_conflict_when_margin_is_wide() -> None:
    scores = {"rule": 0.90, "model": 0.50}
    categories = {"rule": "health", "model": "construction"}

    has_conflict, desc = detect_conflicting_signals(scores, categories, margin=0.15)
    assert has_conflict is False
    assert desc is None


def test_evaluate_confidence_high_level() -> None:
    assessment = evaluate_prediction_confidence(
        0.85,
        scores={"rule": 0.85},
        categories={"rule": "health"},
        category_code="health",
        relevance_tier="high",
    )
    assert assessment.level == ConfidenceLevel.HIGH
    assert assessment.needs_review is False
    assert len(assessment.reasons) == 0


def test_evaluate_confidence_low_level_when_below_threshold() -> None:
    assessment = evaluate_prediction_confidence(
        0.55,
        scores={"semantic": 0.55},
        categories={"semantic": "health"},
        category_code="health",
        relevance_tier="medium",
    )
    assert assessment.level == ConfidenceLevel.LOW
    assert assessment.needs_review is True
    assert ReviewReason.LOW_CONFIDENCE in assessment.reasons


def test_evaluate_confidence_low_level_when_conflicting_signals() -> None:
    assessment = evaluate_prediction_confidence(
        0.82,
        scores={"rule": 0.82, "model": 0.80},
        categories={"rule": "health", "model": "construction"},
        category_code="health",
        relevance_tier="high",
    )
    assert assessment.level == ConfidenceLevel.LOW
    assert assessment.needs_review is True
    assert ReviewReason.CONFLICTING_SIGNALS in assessment.reasons


def test_evaluate_confidence_flags_unassigned_category_on_relevant_tender() -> None:
    assessment = evaluate_prediction_confidence(
        0.70,
        scores={"rule": 0.0, "semantic": 0.45},
        categories={"rule": None, "semantic": None},
        category_code=None,
        relevance_tier="high",
    )
    assert assessment.level == ConfidenceLevel.LOW
    assert assessment.needs_review is True
    assert ReviewReason.UNASSIGNED_CATEGORY in assessment.reasons
