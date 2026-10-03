"""RAG Benchmark and Automated Evaluator (Fase 9.22 / 9.23).

Executes automated evaluation runs across the canonical test dataset,
aggregates Retrieval and Generation metrics, and generates a structured report.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.ai.evaluation.dataset import (
    EvaluationCategory,
    EvaluationDataset,
    EvaluationTestCase,
)
from app.ai.metrics import (
    compute_answer_relevance,
    compute_citation_accuracy,
    compute_context_relevance,
    compute_mrr,
    compute_ndcg,
    compute_precision_at_k,
    compute_recall_at_k,
)

logger = logging.getLogger(__name__)


class TestCaseEvaluationResult(BaseModel):
    """Evaluation output for an individual test case."""

    case_id: str
    category: EvaluationCategory
    question: str
    retrieval_strategy_predicted: str
    retrieval_strategy_expected: str
    retrieval_strategy_match: bool
    recall_at_5: float
    precision_at_5: float
    mrr: float
    ndcg_at_5: float
    context_relevance: float
    faithfulness: float
    answer_relevance: float
    citation_accuracy: float
    latency_ms: float
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSummary(BaseModel):
    """Aggregated benchmark scores across all test cases."""

    total_cases: int
    passed_cases: int
    pass_rate: float
    mean_recall_at_5: float
    mean_precision_at_5: float
    mean_mrr: float
    mean_ndcg_at_5: float
    mean_context_relevance: float
    mean_faithfulness: float
    mean_answer_relevance: float
    mean_citation_accuracy: float
    mean_latency_ms: float
    by_category: dict[str, dict[str, float]] = Field(default_factory=dict)
    results: list[TestCaseEvaluationResult] = Field(default_factory=list)


class RAGEvaluator:
    """Evaluates RAG execution turns against gold benchmarks."""

    def __init__(self, dataset: EvaluationDataset | None = None) -> None:
        self.dataset = dataset or EvaluationDataset.load_canonical()

    def evaluate_test_case(
        self,
        test_case: EvaluationTestCase,
        generated_answer: str,
        retrieved_source_ids: list[str],
        retrieval_strategy_used: str,
        citations: list[dict[str, Any]] | None = None,
        context_text: str = "",
        latency_ms: float = 0.0,
    ) -> TestCaseEvaluationResult:
        """Evaluate a single test case execution against ground truth expectations."""
        citations = citations or []

        # 1. Retrieval Metrics
        recall = compute_recall_at_k(retrieved_source_ids, test_case.gold_sources, k=5)
        precision = compute_precision_at_k(retrieved_source_ids, test_case.gold_sources, k=5)
        mrr = compute_mrr(retrieved_source_ids, test_case.gold_sources)
        ndcg = compute_ndcg(retrieved_source_ids, test_case.gold_sources, k=5)
        ctx_rel = compute_context_relevance(context_text, test_case.question)

        # 2. Generation Metrics
        ans_rel = compute_answer_relevance(generated_answer, test_case.gold_answers)
        sources_meta = [{"id": sid} for sid in retrieved_source_ids]
        cit_acc = compute_citation_accuracy(citations, sources_meta)

        # Approximate claims support from gold answers
        faithfulness = 1.0 if ans_rel >= 0.5 else 0.5

        # Strategy check
        strat_match = retrieval_strategy_used.upper() == test_case.gold_retrieval.upper()

        # Overall pass criteria
        passed = (ans_rel >= 0.5) and (recall >= 0.5 or not test_case.gold_sources) and strat_match

        return TestCaseEvaluationResult(
            case_id=test_case.id,
            category=test_case.category,
            question=test_case.question,
            retrieval_strategy_predicted=retrieval_strategy_used,
            retrieval_strategy_expected=test_case.gold_retrieval,
            retrieval_strategy_match=strat_match,
            recall_at_5=recall,
            precision_at_5=precision,
            mrr=mrr,
            ndcg_at_5=ndcg,
            context_relevance=ctx_rel,
            faithfulness=faithfulness,
            answer_relevance=ans_rel,
            citation_accuracy=cit_acc,
            latency_ms=latency_ms,
            passed=passed,
        )

    def aggregate_results(self, results: list[TestCaseEvaluationResult]) -> BenchmarkSummary:
        """Aggregate evaluation metrics across all cases and by category."""
        if not results:
            return BenchmarkSummary(
                total_cases=0,
                passed_cases=0,
                pass_rate=0.0,
                mean_recall_at_5=0.0,
                mean_precision_at_5=0.0,
                mean_mrr=0.0,
                mean_ndcg_at_5=0.0,
                mean_context_relevance=0.0,
                mean_faithfulness=0.0,
                mean_answer_relevance=0.0,
                mean_citation_accuracy=0.0,
                mean_latency_ms=0.0,
            )

        n = len(results)
        passed = sum(1 for r in results if r.passed)

        by_cat: dict[str, list[TestCaseEvaluationResult]] = {}
        for r in results:
            by_cat.setdefault(r.category.value, []).append(r)

        cat_summary: dict[str, dict[str, float]] = {}
        for cat_name, cat_res in by_cat.items():
            cn = len(cat_res)
            cat_summary[cat_name] = {
                "total": float(cn),
                "pass_rate": round(sum(1 for cr in cat_res if cr.passed) / cn, 4),
                "mean_recall_at_5": round(sum(cr.recall_at_5 for cr in cat_res) / cn, 4),
                "mean_answer_relevance": round(sum(cr.answer_relevance for cr in cat_res) / cn, 4),
                "mean_latency_ms": round(sum(cr.latency_ms for cr in cat_res) / cn, 2),
            }

        return BenchmarkSummary(
            total_cases=n,
            passed_cases=passed,
            pass_rate=round(passed / n, 4),
            mean_recall_at_5=round(sum(r.recall_at_5 for r in results) / n, 4),
            mean_precision_at_5=round(sum(r.precision_at_5 for r in results) / n, 4),
            mean_mrr=round(sum(r.mrr for r in results) / n, 4),
            mean_ndcg_at_5=round(sum(r.ndcg_at_5 for r in results) / n, 4),
            mean_context_relevance=round(sum(r.context_relevance for r in results) / n, 4),
            mean_faithfulness=round(sum(r.faithfulness for r in results) / n, 4),
            mean_answer_relevance=round(sum(r.answer_relevance for r in results) / n, 4),
            mean_citation_accuracy=round(sum(r.citation_accuracy for r in results) / n, 4),
            mean_latency_ms=round(sum(r.latency_ms for r in results) / n, 2),
            by_category=cat_summary,
            results=results,
        )
