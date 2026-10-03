"""Unit tests for RAG Metrics calculations (Fase 9.23)."""

from app.ai.metrics import (
    compute_answer_relevance,
    compute_citation_accuracy,
    compute_context_relevance,
    compute_faithfulness,
    compute_grounding_rate,
    compute_mrr,
    compute_ndcg,
    compute_precision_at_k,
    compute_recall_at_k,
)


def test_compute_recall_at_k():
    gold = ["doc1", "doc2"]
    # Top 5 contains 1 of 2
    assert compute_recall_at_k(["doc1", "doc3"], gold, k=5) == 0.5
    # Top 5 contains all 2
    assert compute_recall_at_k(["doc1", "doc2", "doc3"], gold, k=5) == 1.0
    # Top 2 contains 1 of 2 (second is at position 3)
    assert compute_recall_at_k(["doc1", "doc3", "doc2"], gold, k=2) == 0.5
    # Empty gold
    assert compute_recall_at_k([], [], k=5) == 1.0


def test_compute_precision_at_k():
    gold = ["doc1", "doc2"]
    # 2 retrieved, 1 relevant
    assert compute_precision_at_k(["doc1", "doc3"], gold, k=2) == 0.5
    # 2 retrieved, both relevant
    assert compute_precision_at_k(["doc1", "doc2"], gold, k=2) == 1.0
    # None relevant
    assert compute_precision_at_k(["doc3", "doc4"], gold, k=2) == 0.0


def test_compute_mrr():
    gold = ["doc_gold"]
    # At rank 1
    assert compute_mrr(["doc_gold", "doc2"], gold) == 1.0
    # At rank 2
    assert compute_mrr(["doc1", "doc_gold"], gold) == 0.5
    # At rank 4
    assert compute_mrr(["a", "b", "c", "doc_gold"], gold) == 0.25
    # Not found
    assert compute_mrr(["a", "b", "c"], gold) == 0.0


def test_compute_ndcg():
    gold = ["doc1", "doc2"]
    # Perfect order
    score_perfect = compute_ndcg(["doc1", "doc2", "doc3"], gold, k=3)
    assert score_perfect == 1.0

    # Relevant items lower in ranking
    score_suboptimal = compute_ndcg(["doc3", "doc1", "doc2"], gold, k=3)
    assert 0.0 < score_suboptimal < 1.0

    # No relevant items
    assert compute_ndcg(["a", "b", "c"], gold, k=3) == 0.0


def test_compute_context_relevance():
    query = "licitaciones de sillas de ruedas para hospital"
    relevant_ctx = "Bases para licitaciones de sillas de ruedas motorizadas destinadas a hospital regional."
    assert compute_context_relevance(relevant_ctx, query) >= 0.75

    irrelevant_ctx = "Adquisición de combustible y lubricantes para vehículos municipales."
    assert compute_context_relevance(irrelevant_ctx, query) <= 0.25


def test_compute_faithfulness():
    # 3 claims, 3 verified
    assert compute_faithfulness(["$50M", "2024", "1234-56-LP24"], ["$50M", "2024", "1234-56-LP24"]) == 1.0
    # 3 claims, 2 verified
    assert compute_faithfulness(["$50M", "2024", "1234-56-LP24"], ["$50M", "2024"]) == 0.6667
    # 0 claims
    assert compute_faithfulness([], []) == 1.0


def test_compute_citation_accuracy():
    sources = [{"id": "s1"}, {"id": "s2"}]
    citations = [{"source_id": "s1", "is_verified": True}, {"source_id": "s2", "is_verified": True}]
    assert compute_citation_accuracy(citations, sources) == 1.0

    unverified_citations = [{"source_id": "fake", "is_verified": False}]
    assert compute_citation_accuracy(unverified_citations, sources) == 0.0


def test_compute_grounding_rate():
    scores = [0.95, 0.85, 0.90, 0.40]
    assert compute_grounding_rate(scores, threshold=0.80) == 0.75


def test_compute_answer_relevance():
    gold_phrases = ["$50.000.000 CLP", "Hospital Central"]
    answer = "El gasto del Hospital Central alcanzó los $50.000.000 CLP durante el año."
    assert compute_answer_relevance(answer, gold_phrases) == 1.0

    partial_answer = "El Hospital Central realizó compras."
    assert compute_answer_relevance(partial_answer, gold_phrases) == 0.5
