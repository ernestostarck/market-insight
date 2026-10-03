"""Semantic and Vector Retrieval Engine for MercadoInsight AI (Fase 9.7).

Integrates pgvector cosine similarity search, Phase 6 multilingual sentence embeddings,
metadata filtering, and traceability to original public procurement sources.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from app.ai.contracts import QueryPlan, RetrievalResult, RetrievalStrategy, Source
from app.ai.interfaces import Retriever
from app.ml.embeddings import EmbeddingService as MLEmbeddingService
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository


class SemanticRetriever(Retriever):
    """Semantic vector search engine retrieving similar tenders backed by pgvector."""

    def __init__(
        self,
        vector_repository: VectorSearchRepository,
        embedding_service: MLEmbeddingService | None = None,
        default_top_k: int = 10,
        default_min_similarity: float = 0.20,
    ) -> None:
        self._vector_repo = vector_repository
        self._embedding_service = embedding_service or MLEmbeddingService()
        self._default_top_k = default_top_k
        self._default_min_similarity = default_min_similarity

    async def retrieve(self, plan: QueryPlan) -> RetrievalResult:
        """Execute semantic similarity search using query vector embedding and pgvector."""
        query_text = plan.semantic_query or plan.intent.value
        start_time = time.perf_counter()

        # 1. Generate query vector embedding (384-dim, normalized)
        query_vectors: np.ndarray = self._embedding_service.encode([query_text])
        if len(query_vectors) == 0:
            query_vector = np.zeros(MLEmbeddingService.DIMENSIONS, dtype=np.float32)
        else:
            query_vector = query_vectors[0]

        # 2. Extract retrieval parameters from plan filters
        filters = plan.filters or {}
        params = plan.parameters or {}

        top_k = int(params.get("top_k", self._default_top_k))
        min_similarity = float(params.get("min_similarity", self._default_min_similarity))
        category_code = filters.get("category_code")

        # 3. Query pgvector index in knowledge.embeddings
        similar_tenders: list[SimilarLicitacion] = await self._vector_repo.search_by_vector(
            query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
            category_code=category_code,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 4. Transform results into structured items and verifiable Source citations
        items: list[dict[str, Any]] = []
        sources: list[Source] = []

        for item in similar_tenders:
            tender_dict = {
                "licitacion_id": item.licitacion_id,
                "nombre": item.nombre,
                "similarity": round(item.similarity, 4),
                "category_id": item.category_id,
                "subcategory_id": item.subcategory_id,
            }
            items.append(tender_dict)

            title = item.nombre or f"Licitación {item.licitacion_id}"
            url = f"https://mercadopublico.cl/tender/{item.licitacion_id}"
            snippet = f"Licitación ID {item.licitacion_id}: {title}. Similitud semántica calculada: {item.similarity:.2%}."

            sources.append(
                Source(
                    id=str(item.licitacion_id),
                    source_type="tender",
                    title=title,
                    url=url,
                    snippet=snippet,
                    score=round(item.similarity, 4),
                    metadata=tender_dict,
                )
            )

        return RetrievalResult(
            strategy_used=RetrievalStrategy.SEMANTIC,
            items=items,
            sources=sources,
            execution_time_ms=round(elapsed_ms, 2),
            total_results=len(items),
        )
