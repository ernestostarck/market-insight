"""Unit tests for Evaluation Dataset and RAGEvaluator (Fase 9.22)."""

from app.ai.evaluation.dataset import EvaluationCategory, EvaluationDataset
from app.ai.evaluation.evaluator import RAGEvaluator


def test_canonical_dataset_loads_and_has_all_categories():
    dataset = EvaluationDataset.load_canonical()

    assert dataset.name == "mercado_insight_rag_gold_benchmark"
    assert len(dataset.test_cases) >= 12

    # Verify all 8 required categories are represented
    found_categories = {tc.category for tc in dataset.test_cases}
    expected_categories = {
        EvaluationCategory.QUANTITATIVE,
        EvaluationCategory.SEMANTIC,
        EvaluationCategory.HYBRID,
        EvaluationCategory.CONTEXTUAL,
        EvaluationCategory.NO_EVIDENCE,
        EvaluationCategory.AMBIGUOUS,
        EvaluationCategory.ADVERSARIAL,
        EvaluationCategory.PROMPT_INJECTION,
    }

    assert expected_categories.issubset(found_categories)


def test_dataset_filter_by_category():
    dataset = EvaluationDataset.load_canonical()
    quant_cases = dataset.filter_by_category(EvaluationCategory.QUANTITATIVE)
    assert len(quant_cases) >= 2
    for tc in quant_cases:
        assert tc.category == EvaluationCategory.QUANTITATIVE
        assert tc.gold_retrieval == "SQL"


def test_rag_evaluator_evaluates_test_case_success():
    evaluator = RAGEvaluator()
    dataset = evaluator.dataset

    tc = dataset.test_cases[0]  # gold-quant-01
    result = evaluator.evaluate_test_case(
        test_case=tc,
        generated_answer="El Hospital Central gastó $50.000.000 CLP en 2024.",
        retrieved_source_ids=["1234-56-LP24", "9999-99-LR24"],
        retrieval_strategy_used="SQL",
        citations=[{"source_id": "1234-56-LP24", "is_verified": True}],
        context_text="Hospital Central gastó $50.000.000 CLP.",
        latency_ms=150.0,
    )

    assert result.case_id == tc.id
    assert result.retrieval_strategy_match is True
    assert result.recall_at_5 == 1.0
    assert result.precision_at_5 == 0.5
    assert result.mrr == 1.0
    assert result.answer_relevance >= 0.5
    assert result.passed is True


def test_rag_evaluator_aggregate_results():
    evaluator = RAGEvaluator()
    tc = evaluator.dataset.test_cases[0]

    res1 = evaluator.evaluate_test_case(
        test_case=tc,
        generated_answer=tc.expected_answer,
        retrieved_source_ids=tc.gold_sources,
        retrieval_strategy_used=tc.gold_retrieval,
        citations=[],
        latency_ms=100.0,
    )
    res2 = evaluator.evaluate_test_case(
        test_case=tc,
        generated_answer="Respuesta irrelevante.",
        retrieved_source_ids=[],
        retrieval_strategy_used="DIRECT",
        citations=[],
        latency_ms=80.0,
    )

    summary = evaluator.aggregate_results([res1, res2])

    assert summary.total_cases == 2
    assert summary.passed_cases == 1
    assert summary.pass_rate == 0.5
    assert summary.mean_latency_ms == 90.0
    assert "quantitative" in summary.by_category
