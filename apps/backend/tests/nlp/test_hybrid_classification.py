from app.nlp.hybrid_classification import SignalResult, combine_signals


def test_highest_score_wins() -> None:
    signals = (
        SignalResult("rule", "health", "medical-equipment", 0.4),
        SignalResult("semantic", "construction", "civil-works", 0.9),
        SignalResult("model", "health", "assistive-technology", 0.6),
    )

    result = combine_signals(signals)

    assert result.category_code == "construction"
    assert result.subcategory_code == "civil-works"
    assert result.winning_method == "semantic"
    assert result.confidence_score == 0.9


def test_signals_without_a_category_do_not_compete() -> None:
    signals = (
        SignalResult("rule", None, None, 0.0),
        SignalResult("semantic", None, None, 0.3),
        SignalResult("model", "health", "geriatric-care", 0.2),
    )

    result = combine_signals(signals)

    assert result.category_code == "health"
    assert result.winning_method == "model"
    assert result.confidence_score == 0.2


def test_all_signals_empty_returns_no_category() -> None:
    signals = (
        SignalResult("rule", None, None, 0.0),
        SignalResult("semantic", None, None, 0.2),
        SignalResult("model", None, None, 0.1),
    )

    result = combine_signals(signals)

    assert result.category_code is None
    assert result.winning_method is None
    assert result.confidence_score == 0.2


def test_tie_breaks_toward_rule_over_model_and_semantic() -> None:
    signals = (
        SignalResult("semantic", "construction", "civil-works", 0.5),
        SignalResult("model", "technology", "hardware", 0.5),
        SignalResult("rule", "health", "medical-equipment", 0.5),
    )

    result = combine_signals(signals)

    assert result.winning_method == "rule"
    assert result.category_code == "health"


def test_tie_breaks_toward_model_over_semantic() -> None:
    signals = (
        SignalResult("semantic", "construction", "civil-works", 0.5),
        SignalResult("model", "technology", "hardware", 0.5),
    )

    result = combine_signals(signals)

    assert result.winning_method == "model"


def test_explanation_records_all_scores_and_winner() -> None:
    signals = (
        SignalResult("rule", "health", "medical-equipment", 0.4),
        SignalResult("semantic", None, None, 0.1),
    )

    result = combine_signals(signals)

    assert result.explanation["scores"] == {"rule": 0.4, "semantic": 0.1}
    assert result.explanation["categories"] == {"rule": "health"}
    assert result.explanation["winning_method"] == "rule"


def test_no_signals_at_all_returns_empty_result() -> None:
    result = combine_signals(())

    assert result.category_code is None
    assert result.confidence_score == 0.0
