"""Unit tests for Reranker and RerankingMetrics (Fase 9.9)."""

from app.ai.reranker import Reranker, RerankingMetrics


def test_reranker_weighted_scoring_and_ordering():
    candidates = [
        {
            "licitacion_id": "1001",
            "semantic_score": 0.85,
            "lexical_score": 0.20,
            "region": "Metropolitana",
        },
        {
            "licitacion_id": "1002",
            "semantic_score": 0.30,
            "lexical_score": 0.85,
            "region": "Valparaiso",
        },
        {
            "licitacion_id": "1003",
            "semantic_score": 0.95,
            "lexical_score": 0.90,
            "region": "Metropolitana",
        },
    ]

    reranker = Reranker(
        weight_semantic=0.55,
        weight_lexical=0.35,
        weight_metadata=0.10,
        min_score=0.2,
    )

    top_items, metrics = reranker.rerank(
        candidates,
        top_k=2,
        metadata_filters={"region": "Metropolitana"},
    )

    assert len(top_items) == 2
    # 1003 should be ranked first due to high semantic + high lexical + metadata match
    assert top_items[0]["licitacion_id"] == "1003"
    assert top_items[0]["rerank_score"] > top_items[1]["rerank_score"]

    assert isinstance(metrics, RerankingMetrics)
    assert metrics.total_candidates == 3
    assert metrics.kept_candidates == 2
    assert metrics.filtered_out == 0
    assert metrics.recall_at_k > 0.0


def test_reranker_threshold_filtering():
    candidates = [
        {"licitacion_id": "low-1", "semantic_score": 0.05, "lexical_score": 0.02},
        {"licitacion_id": "high-1", "semantic_score": 0.80, "lexical_score": 0.70},
    ]

    # Set threshold high so low-1 is filtered out
    reranker = Reranker(min_score=0.40)
    top_items, metrics = reranker.rerank(candidates, top_k=5)

    assert len(top_items) == 1
    assert top_items[0]["licitacion_id"] == "high-1"
    assert metrics.filtered_out == 1


def test_reranker_metadata_bonus():
    reranker = Reranker()
    item = {"region": "Metropolitana", "tipo": "LP"}

    # Perfect match
    score_both = reranker.compute_metadata_bonus(item, {"region": "Metropolitana", "tipo": "LP"})
    assert score_both == 1.0

    # Half match
    score_half = reranker.compute_metadata_bonus(item, {"region": "Metropolitana", "tipo": "LR"})
    assert score_half == 0.5

    # No filter provided -> neutral 0.5
    score_none = reranker.compute_metadata_bonus(item, None)
    assert score_none == 0.5


def test_reranker_empty_candidates():
    reranker = Reranker()
    top_items, metrics = reranker.rerank([])

    assert top_items == []
    assert metrics.total_candidates == 0
    assert metrics.kept_candidates == 0
    assert metrics.recall_at_k == 1.0
