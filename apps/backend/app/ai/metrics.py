"""RAG Evaluation Metrics calculation engine (Fase 9.23).

Provides deterministic formulas for:
1. Retrieval Metrics:
   - Recall@K
   - Precision@K
   - MRR (Mean Reciprocal Rank)
   - NDCG (Normalized Discounted Cumulative Gain)
   - Context Relevance
2. Generation Metrics:
   - Faithfulness (Factual consistency / grounding)
   - Answer Relevance (Coverage of key factual concepts)
   - Citation Accuracy (% verified sources)
   - Grounding Rate
3. System Metrics:
   - Latency breakdowns, token usage, error rates
"""

from __future__ import annotations

import math
import re
from typing import Any


def compute_recall_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 5) -> float:
    """Proportion of relevant gold items retrieved within the top K results."""
    if not gold_ids:
        # If no gold sources are expected (e.g. out of scope or no evidence), empty retrieved is 1.0, otherwise 0.0
        return 1.0 if not retrieved_ids[:k] else 0.0

    top_k = retrieved_ids[:k]
    matched = set(top_k).intersection(set(gold_ids))
    return round(len(matched) / len(gold_ids), 4)


def compute_precision_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int = 5) -> float:
    """Proportion of top K retrieved items that are relevant."""
    top_k = retrieved_ids[:k]
    if not top_k:
        return 1.0 if not gold_ids else 0.0

    matched = set(top_k).intersection(set(gold_ids))
    return round(len(matched) / len(top_k), 4)


def compute_mrr(retrieved_ids: list[str], gold_ids: list[str]) -> float:
    """Mean Reciprocal Rank: inverse of the rank of the first relevant document."""
    if not gold_ids:
        return 1.0 if not retrieved_ids else 0.0

    gold_set = set(gold_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in gold_set:
            return round(1.0 / rank, 4)
    return 0.0


def compute_ndcg(retrieved_ids: list[str], gold_ids: list[str], k: int = 5) -> float:
    """Normalized Discounted Cumulative Gain at rank K with binary relevance."""
    if not gold_ids:
        return 1.0 if not retrieved_ids[:k] else 0.0

    gold_set = set(gold_ids)
    top_k = retrieved_ids[:k]

    # Calculate DCG@K
    dcg = 0.0
    for i, doc_id in enumerate(top_k):
        rel = 1.0 if doc_id in gold_set else 0.0
        dcg += rel / math.log2(i + 2)

    # Calculate Ideal DCG@K (IDCG)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold_ids), k)))

    if idcg == 0.0:
        return 0.0

    return round(dcg / idcg, 4)


def compute_context_relevance(
    context_text: str,
    query: str,
    gold_snippets: list[str] | None = None,
) -> float:
    """Measure the degree to which retrieved context text is relevant to query keywords."""
    if not context_text or not query:
        return 0.0

    # Extract query words > 3 characters
    keywords = [w.lower() for w in re.findall(r"\b\w{4,}\b", query)]
    if not keywords:
        return 1.0

    ctx_lower = context_text.lower()
    matches = sum(1 for kw in keywords if kw in ctx_lower)
    score = matches / len(keywords)

    if gold_snippets:
        snippet_matches = sum(1 for snip in gold_snippets if snip.lower() in ctx_lower)
        snippet_ratio = snippet_matches / len(gold_snippets)
        score = 0.5 * score + 0.5 * snippet_ratio

    return round(min(1.0, max(0.0, score)), 4)


def compute_faithfulness(claims: list[str], verified_claims: list[str]) -> float:
    """Proportion of factual claims supported directly by source context."""
    if not claims:
        return 1.0
    return round(len(verified_claims) / len(claims), 4)


def compute_citation_accuracy(citations: list[dict[str, Any]], sources: list[dict[str, Any]]) -> float:
    """Proportion of emitted citations that match verified sources."""
    if not citations:
        # If no citations were generated, 1.0 if no sources were available, else 0.0
        return 1.0 if not sources else 0.5

    source_ids = {str(s.get("id")) for s in sources if s.get("id")}
    valid_citations = 0

    for cit in citations:
        cit_id = str(cit.get("source_id") or cit.get("id") or "")
        is_verified = cit.get("is_verified", False)
        if is_verified or (cit_id and cit_id in source_ids):
            valid_citations += 1

    return round(valid_citations / len(citations), 4)


def compute_grounding_rate(grounding_scores: list[float], threshold: float = 0.8) -> float:
    """Percentage of responses that meet or exceed the grounding threshold."""
    if not grounding_scores:
        return 1.0
    grounded = sum(1 for s in grounding_scores if s >= threshold)
    return round(grounded / len(grounding_scores), 4)


def compute_answer_relevance(answer: str, expected_phrases: list[str]) -> float:
    """Proportion of expected gold facts or phrases present in the generated answer."""
    if not expected_phrases:
        return 1.0

    ans_lower = answer.lower()
    hits = sum(1 for p in expected_phrases if p.lower() in ans_lower)
    return round(hits / len(expected_phrases), 4)
