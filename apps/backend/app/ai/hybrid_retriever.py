"""Hybrid Retrieval Engine for MercadoInsight AI (Fase 9.8).

Combines lexical full-text search (tsvector/ts_rank), semantic vector search (pgvector),
and structured metadata filtering (category, concept, dates, region) with deduplication
and score normalization.
"""

from __future__ import annotations

import time
from typing import Any

from app.ai.contracts import QueryPlan, RetrievalResult, RetrievalStrategy, Source
from app.ai.interfaces import Retriever
from app.ml.embeddings import EmbeddingService as MLEmbeddingService
from app.repositories.hybrid_search import HybridSearchRepository, TextMatch
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository


class HybridRetriever(Retriever):
    """Retrieval engine executing unified lexical, semantic, and metadata-filtered search."""

    def __init__(
        self,
        hybrid_repo: HybridSearchRepository,
        vector_repo: VectorSearchRepository,
        embedding_service: MLEmbeddingService | None = None,
        default_top_k: int = 10,
    ) -> None:
        self._hybrid_repo = hybrid_repo
        self._vector_repo = vector_repo
        self._embedding_service = embedding_service or MLEmbeddingService()
        self._default_top_k = default_top_k

    async def retrieve(self, plan: QueryPlan) -> RetrievalResult:
        """Execute hybrid search combining fulltext and pgvector, applying structured filters."""
        query_text = plan.semantic_query or plan.intent.value
        start_time = time.perf_counter()

        filters = plan.filters or {}
        params = plan.parameters or {}
        top_k = int(params.get("top_k", self._default_top_k))
        fanout = top_k * 3

        category_code = filters.get("category_code")
        min_similarity = float(params.get("min_similarity", 0.0))

        # 1. Lexical Full-text Search
        fulltext_matches: list[TextMatch] = await self._hybrid_repo.search_fulltext(
            query_text, limit=fanout
        )

        # 2. Semantic Vector Search
        query_vectors = self._embedding_service.encode([query_text])
        if len(query_vectors) > 0:
            query_vector = query_vectors[0]
            vector_matches: list[SimilarLicitacion] = await self._vector_repo.search_by_vector(
                query_vector,
                top_k=fanout,
                min_similarity=min_similarity,
                category_code=category_code,
            )
        else:
            vector_matches = []

        # 3. Combine and Deduplicate Results by licitacion_id
        # Normalize ts_rank to [0, 1] relative to max observed rank
        max_rank = max((m.rank for m in fulltext_matches), default=1.0) or 1.0

        candidates: dict[int, dict[str, Any]] = {}

        for m in fulltext_matches:
            normalized_lexical = min(1.0, m.rank / max_rank)
            candidates[m.licitacion_id] = {
                "licitacion_id": m.licitacion_id,
                "nombre": m.nombre,
                "codigo": m.codigo,
                "lexical_score": normalized_lexical,
                "semantic_score": 0.0,
                "matched_via": ["fulltext"],
                "category_id": None,
                "subcategory_id": None,
            }

        for v in vector_matches:
            if v.licitacion_id in candidates:
                cand = candidates[v.licitacion_id]
                cand["semantic_score"] = v.similarity
                cand["matched_via"].append("semantic")
                if v.nombre and not cand.get("nombre"):
                    cand["nombre"] = v.nombre
                cand["category_id"] = v.category_id
                cand["subcategory_id"] = v.subcategory_id
            else:
                candidates[v.licitacion_id] = {
                    "licitacion_id": v.licitacion_id,
                    "nombre": v.nombre,
                    "codigo": None,
                    "lexical_score": 0.0,
                    "semantic_score": v.similarity,
                    "matched_via": ["semantic"],
                    "category_id": v.category_id,
                    "subcategory_id": v.subcategory_id,
                }

        # 4. Compute unified hybrid score (balanced average with matched-via boost)
        scored_items: list[dict[str, Any]] = []
        for cand in candidates.values():
            lex = cand["lexical_score"]
            sem = cand["semantic_score"]
            # Dual match gets synergy boost
            if "fulltext" in cand["matched_via"] and "semantic" in cand["matched_via"]:
                combined_score = 0.5 * sem + 0.4 * lex + 0.1
            elif "semantic" in cand["matched_via"]:
                combined_score = 0.8 * sem
            else:
                combined_score = 0.8 * lex

            cand["hybrid_score"] = round(min(1.0, max(0.0, combined_score)), 4)
            scored_items.append(cand)

        # Sort by unified hybrid score descending
        scored_items.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_items = scored_items[:top_k]

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 5. Build Source Citations
        sources: list[Source] = []
        for item in top_items:
            lic_id = item["licitacion_id"]
            title = item.get("nombre") or f"Licitación {lic_id}"
            url = f"https://mercadopublico.cl/tender/{lic_id}"
            channels = "+".join(item["matched_via"])
            snippet = f"Licitación ID {lic_id}: {title}. Match vía: [{channels}]. Score: {item['hybrid_score']:.2%}."

            sources.append(
                Source(
                    id=str(lic_id),
                    source_type="tender",
                    title=title,
                    url=url,
                    snippet=snippet,
                    score=item["hybrid_score"],
                    metadata=item,
                )
            )

        return RetrievalResult(
            strategy_used=RetrievalStrategy.HYBRID,
            items=top_items,
            sources=sources,
            execution_time_ms=round(elapsed_ms, 2),
            total_results=len(top_items),
        )
