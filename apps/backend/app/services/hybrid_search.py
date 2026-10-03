"""Combine full-text and semantic search into one ranked result (Fase 6.10).

See docs/07-ai/hybrid-search.md for why embedding the query text here is a
deliberate, different decision from the "no inference in the request path"
rule that governs licitacion-document embeddings (app/nlp/semantic.py) —
short summary: there's no way to precompute an embedding for arbitrary
user queries, and embedding a few words is cheap, unlike a full document.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.ml.embeddings import EmbeddingService
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_vectors import build_category_vectors, build_concept_vectors
from app.repositories.hybrid_search import HybridSearchRepository, TextMatch
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository

# Standard constant from the original Reciprocal Rank Fusion formulation,
# widely reused as-is in hybrid search systems. ts_rank (unbounded, corpus-
# dependent) and cosine similarity (bounded 0-1) aren't directly comparable
# — RRF sidesteps that by only using each list's *rank*, not its raw score.
# Real tuning is 6.23 (MLOps & Evaluation), same spirit as the other
# initial-heuristic constants in 6.7-6.9.
_RRF_K = 60


@dataclass(frozen=True, slots=True)
class HybridSearchResult:
    licitacion_id: int
    nombre: str | None
    codigo: str | None
    score: float
    matched_via: frozenset[str]


class HybridSearchService:
    def __init__(
        self,
        repository: HybridSearchRepository,
        vector_repository: VectorSearchRepository,
        embedding_service: EmbeddingService,
        taxonomy: Taxonomy | None = None,
    ) -> None:
        self._repository = repository
        self._vector_repository = vector_repository
        self._embedding_service = embedding_service
        self._taxonomy = taxonomy or load_initial_taxonomy()
        self._concept_vectors = build_concept_vectors(self._taxonomy, embedding_service)
        self._category_vectors = build_category_vectors(self._taxonomy, embedding_service)

    async def search(self, query: str, *, top_k: int = 10) -> list[HybridSearchResult]:
        # Sequential, not asyncio.gather: search_fulltext/search_by_vector share
        # one AsyncSession, which SQLAlchemy does not allow to run concurrently
        # (raises InvalidRequestError — confirmed against real Postgres).
        fanout = top_k * 3
        query_vector = self._embedding_service.encode([query])[0]
        fulltext = await self._repository.search_fulltext(query, limit=fanout)
        semantic = await self._vector_repository.search_by_vector(query_vector, top_k=fanout, min_similarity=0.0)
        return _combine(fulltext, semantic)[:top_k]

    async def search_by_code(self, code: str, *, top_k: int = 10) -> list[TextMatch]:
        return await self._repository.search_by_code(code, limit=top_k)

    async def search_products(self, query: str, *, top_k: int = 10) -> list[TextMatch]:
        return await self._repository.search_products(query, limit=top_k)

    async def search_by_concept(self, concept_code: str, *, top_k: int = 10) -> list[SimilarLicitacion]:
        return await self._vector_repository.search_by_concept(concept_code, self._concept_vectors, top_k=top_k)

    async def search_by_category(self, category_code: str, *, top_k: int = 10) -> list[SimilarLicitacion]:
        return await self._vector_repository.search_by_category(category_code, self._category_vectors, top_k=top_k)


def _combine(fulltext: list[TextMatch], semantic: list[SimilarLicitacion]) -> list[HybridSearchResult]:
    scores: dict[int, float] = defaultdict(float)
    matched_via: dict[int, set[str]] = defaultdict(set)
    nombre_by_id: dict[int, str | None] = {}
    codigo_by_id: dict[int, str | None] = {}

    for rank, match in enumerate(fulltext, start=1):
        scores[match.licitacion_id] += 1.0 / (_RRF_K + rank)
        matched_via[match.licitacion_id].add("fulltext")
        nombre_by_id[match.licitacion_id] = match.nombre
        codigo_by_id[match.licitacion_id] = match.codigo

    for rank, match in enumerate(semantic, start=1):
        scores[match.licitacion_id] += 1.0 / (_RRF_K + rank)
        matched_via[match.licitacion_id].add("semantic")
        nombre_by_id.setdefault(match.licitacion_id, match.nombre)
        codigo_by_id.setdefault(match.licitacion_id, None)

    results = [
        HybridSearchResult(
            licitacion_id=licitacion_id, nombre=nombre_by_id.get(licitacion_id),
            codigo=codigo_by_id.get(licitacion_id), score=score,
            matched_via=frozenset(matched_via[licitacion_id]),
        )
        for licitacion_id, score in scores.items()
    ]
    results.sort(key=lambda item: (-item.score, item.licitacion_id))
    return results
