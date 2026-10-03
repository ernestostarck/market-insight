"""Reranking Engine for MercadoInsight AI (Fase 9.9).

Combines lexical signals, semantic signals, and metadata match bonuses through weighted
scoring and Reciprocal Rank Fusion (RRF), filtering irrelevant candidates and tracking
Recall@K metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_DEFAULT_RRF_K = 60


@dataclass(frozen=True, slots=True)
class RerankingMetrics:
    """Metrics assessing reranking efficacy and candidate retention."""

    total_candidates: int
    kept_candidates: int
    filtered_out: int
    overlap_ratio: float
    recall_at_k: float


class Reranker:
    """Reranks candidate evidence items using multi-signal scoring and RRF."""

    def __init__(
        self,
        weight_semantic: float = 0.55,
        weight_lexical: float = 0.35,
        weight_metadata: float = 0.10,
        rrf_k: int = _DEFAULT_RRF_K,
        min_score: float = 0.15,
    ) -> None:
        self.weight_semantic = weight_semantic
        self.weight_lexical = weight_lexical
        self.weight_metadata = weight_metadata
        self.rrf_k = rrf_k
        self.min_score = min_score

    def compute_metadata_bonus(
        self,
        item: dict[str, Any],
        metadata_filters: dict[str, Any] | None,
    ) -> float:
        """Compute match score [0.0, 1.0] against target metadata filters."""
        if not metadata_filters:
            return 0.5  # Neutral bonus when no specific filter is asserted

        matches = 0
        total = len(metadata_filters)

        for key, target_val in metadata_filters.items():
            if str(item.get(key, "")).lower() == str(target_val).lower():
                matches += 1

        return matches / total if total > 0 else 0.0

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        top_k: int = 10,
        metadata_filters: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], RerankingMetrics]:
        """Combine signals, filter irrelevant items, apply RRF, and return top-k with metrics."""
        total_input = len(candidates)
        if total_input == 0:
            return [], RerankingMetrics(0, 0, 0, 1.0, 1.0)

        # Baseline: initial top_k candidate IDs before reranking
        initial_top_ids = {c.get("licitacion_id") for c in candidates[:top_k] if c.get("licitacion_id")}

        reranked_items: list[dict[str, Any]] = []

        for rank_idx, cand in enumerate(candidates, start=1):
            item = dict(cand)

            sem_score = float(item.get("semantic_score", 0.0))
            lex_score = float(item.get("lexical_score", 0.0))
            meta_score = self.compute_metadata_bonus(item, metadata_filters)

            # 1. Weighted linear signal combination
            weighted_score = (
                self.weight_semantic * sem_score
                + self.weight_lexical * lex_score
                + self.weight_metadata * meta_score
            )

            # 2. Reciprocal Rank Fusion component
            rrf_score = 1.0 / (self.rrf_k + rank_idx)

            final_score = round(min(1.0, max(0.0, weighted_score + (rrf_score * 5.0))), 4)

            # 3. Discard irrelevant results below min_score threshold
            if final_score < self.min_score:
                continue

            item["rerank_score"] = final_score
            reranked_items.append(item)

        # Sort by final rerank_score descending
        reranked_items.sort(key=lambda x: x["rerank_score"], reverse=True)
        final_top = reranked_items[:top_k]

        # 4. Measure Metrics (Overlap & Recall@K)
        final_top_ids = {c.get("licitacion_id") for c in final_top if c.get("licitacion_id")}
        overlap_count = len(initial_top_ids.intersection(final_top_ids))
        overlap_ratio = round(overlap_count / len(initial_top_ids), 4) if initial_top_ids else 1.0

        # Recall@K assesses preservation of high-affinity candidates
        high_affinity_count = sum(1 for c in candidates if float(c.get("semantic_score", 0.0)) >= 0.70)
        recalled_in_k = sum(1 for c in final_top if float(c.get("semantic_score", 0.0)) >= 0.70)
        recall_at_k = round(recalled_in_k / high_affinity_count, 4) if high_affinity_count > 0 else 1.0

        metrics = RerankingMetrics(
            total_candidates=total_input,
            kept_candidates=len(final_top),
            filtered_out=total_input - len(reranked_items),
            overlap_ratio=overlap_ratio,
            recall_at_k=recall_at_k,
        )

        return final_top, metrics
