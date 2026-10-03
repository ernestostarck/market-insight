"""Semantic search application service (Fase 6.18)."""

from __future__ import annotations

from app.ml.embeddings import EmbeddingService as MLEmbeddingService
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_vectors import build_category_vectors, build_concept_vectors
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository


class SemanticSearchService:
    def __init__(
        self,
        vector_repository: VectorSearchRepository,
        embedding_service: MLEmbeddingService,
        taxonomy: Taxonomy | None = None,
    ) -> None:
        self._vector_repo = vector_repository
        self._embedding_service = embedding_service
        self._taxonomy = taxonomy or load_initial_taxonomy()
        self._concept_vectors = build_concept_vectors(self._taxonomy, embedding_service)
        self._category_vectors = build_category_vectors(self._taxonomy, embedding_service)

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
        category_code: str | None = None,
    ) -> list[SimilarLicitacion]:
        query_vector = self._embedding_service.encode([query])[0]
        return await self._vector_repo.search_by_vector(
            query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
            category_code=category_code,
        )

    async def find_similar_to_licitacion(
        self, licitacion_id: int, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        return await self._vector_repo.find_similar_to_licitacion(
            licitacion_id, top_k=top_k, min_similarity=min_similarity
        )

    async def search_by_concept(
        self, concept_code: str, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        return await self._vector_repo.search_by_concept(
            concept_code, self._concept_vectors, top_k=top_k, min_similarity=min_similarity
        )

    async def search_by_category(
        self, category_code: str, *, top_k: int = 10, min_similarity: float = 0.0
    ) -> list[SimilarLicitacion]:
        return await self._vector_repo.search_by_category(
            category_code, self._category_vectors, top_k=top_k, min_similarity=min_similarity
        )
