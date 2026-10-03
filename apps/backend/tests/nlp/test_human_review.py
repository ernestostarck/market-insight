from app.nlp.confidence import ReviewReason
from app.nlp.human_review import (
    ReviewDecision,
    compute_review_priority,
    validate_review_decision,
)

_VALID_CATEGORIES = {"health", "construction", "technology"}
_VALID_SUBCATEGORIES = {
    "health": {"geriatric-care", "assistive-technology"},
    "construction": {"accessibility-adaptation"},
    "technology": {"software", "hardware"},
}


def test_validate_accepted_decision_is_valid() -> None:
    decision = ReviewDecision(
        accepted=True,
        relevant=True,
        category_code="health",
        subcategory_code="geriatric-care",
        relevance_tier="high",
        reason=None,
    )
    errors = validate_review_decision(
        decision,
        valid_categories=_VALID_CATEGORIES,
        subcategories_by_category=_VALID_SUBCATEGORIES,
    )
    assert errors == []


def test_validate_modification_requires_reason() -> None:
    decision = ReviewDecision(
        accepted=False,
        relevant=True,
        category_code="health",
        subcategory_code="geriatric-care",
        relevance_tier="high",
        reason="",  # empty
    )
    errors = validate_review_decision(
        decision,
        valid_categories=_VALID_CATEGORIES,
        subcategories_by_category=_VALID_SUBCATEGORIES,
    )
    assert any("motivo (reason) es requerido" in err for err in errors)


def test_validate_not_relevant_must_not_have_categories() -> None:
    decision = ReviewDecision(
        accepted=False,
        relevant=False,
        category_code="health",  # should be None
        subcategory_code=None,
        relevance_tier="not_relevant",
        reason="Falso positivo, licitación no pertenece al dominio.",
    )
    errors = validate_review_decision(
        decision,
        valid_categories=_VALID_CATEGORIES,
        subcategories_by_category=_VALID_SUBCATEGORIES,
    )
    assert any("no debe tener category_code" in err for err in errors)


def test_validate_invalid_category_detected() -> None:
    decision = ReviewDecision(
        accepted=False,
        relevant=True,
        category_code="unknown-category",
        subcategory_code=None,
        relevance_tier="medium",
        reason="Corrección a categoría desconocida.",
    )
    errors = validate_review_decision(
        decision,
        valid_categories=_VALID_CATEGORIES,
        subcategories_by_category=_VALID_SUBCATEGORIES,
    )
    assert any("no existe en la taxonomía" in err for err in errors)


def test_validate_mismatched_subcategory_detected() -> None:
    decision = ReviewDecision(
        accepted=False,
        relevant=True,
        category_code="health",
        subcategory_code="accessibility-adaptation",  # belongs to construction, not health
        relevance_tier="high",
        reason="Corrección de subcategoría.",
    )
    errors = validate_review_decision(
        decision,
        valid_categories=_VALID_CATEGORIES,
        subcategories_by_category=_VALID_SUBCATEGORIES,
    )
    assert any("no pertenece a la categoría" in err for err in errors)


def test_compute_review_priority_ranks_uncertain_relevant_tenders_highest() -> None:
    high_rel_low_conf = compute_review_priority(
        relevance_tier="high",
        relevance_score=0.85,
        confidence_score=0.40,
        reasons=[ReviewReason.LOW_CONFIDENCE, ReviewReason.CONFLICTING_SIGNALS],
    )
    low_rel_high_conf = compute_review_priority(
        relevance_tier="low",
        relevance_score=0.10,
        confidence_score=0.90,
        reasons=[],
    )

    assert high_rel_low_conf > low_rel_high_conf
    assert high_rel_low_conf > 1.0  # Boosted by risk factors
