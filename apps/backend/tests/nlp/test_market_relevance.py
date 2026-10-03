from app.nlp.market_relevance import ALGORITHM_VERSION, compute_relevance


def test_rule_signal_dominates_when_saturated() -> None:
    result = compute_relevance(rule_score=3.0, similarity_score=0.2, model_score=0.1, still_open=True)

    assert result.thematic_score == 1.0
    assert result.relevance_score == 1.0
    assert result.relevance_tier == "high"


def test_similarity_signal_dominates() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.7, model_score=0.1, still_open=True)

    assert result.thematic_score == 0.7
    assert result.relevance_score == 0.7
    assert result.relevance_tier == "high"


def test_model_signal_dominates() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.1, model_score=0.9, still_open=True)

    assert result.thematic_score == 0.9
    assert result.relevance_score == 0.9


def test_all_signals_zero_is_not_relevant() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.0, model_score=0.0, still_open=True)

    assert result.relevance_score == 0.0
    assert result.relevance_tier == "not_relevant"


def test_rule_score_above_saturation_clamps_to_one() -> None:
    result = compute_relevance(rule_score=6.0, similarity_score=0.0, model_score=0.0, still_open=True)

    assert result.thematic_score == 1.0


def test_closed_licitacion_discounts_but_does_not_zero_relevance() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.8, model_score=0.0, still_open=False)

    assert result.thematic_score == 0.8
    assert result.commercial_score == 0.5
    assert result.relevance_score == 0.4
    assert result.relevance_tier == "medium"


def test_tier_boundary_high() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.66, model_score=0.0, still_open=True)

    assert result.relevance_tier == "high"


def test_tier_boundary_medium() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.33, model_score=0.0, still_open=True)

    assert result.relevance_tier == "medium"


def test_tier_boundary_low() -> None:
    result = compute_relevance(rule_score=0.0, similarity_score=0.01, model_score=0.0, still_open=True)

    assert result.relevance_tier == "low"


def test_explanation_records_breakdown() -> None:
    result = compute_relevance(rule_score=1.5, similarity_score=0.4, model_score=0.3, still_open=False)

    assert result.explanation == {
        "algorithm_version": ALGORITHM_VERSION,
        "thematic_score": result.thematic_score,
        "commercial_score": 0.5,
        "still_open": False,
    }
