"""Real pgvector similarity search over `knowledge.embeddings` (Fase 6.9).

Async, `AsyncSession` — same style as `AnalyticsRepository`
(app/repositories/analytics.py) — but raw SQL via `text()` for the vector
distance operator (`<=>`, `vector_cosine_ops`): SQLAlchemy's expression
language has no operator for the custom `Vector` type (app/models/
knowledge.py), same reason 6.6-6.8 already use `text()` for that column.

Only the most recent embedding per licitacion is searched (a licitacion can
be re-embedded after its document changes) — comparing vectors from
different embedding models would be meaningless, and today there is only
ever one model in play, so "most recent" is the correct and sufficient
rule for now.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.nlp.taxonomy_vectors import CategoryVector, ConceptVector

_SEARCH_SQL = """
WITH latest_embeddings AS (
    SELECT DISTINCT ON (licitacion_id) licitacion_id, vector
    FROM knowledge.embeddings
    ORDER BY licitacion_id, created_at DESC
)
SELECT
    le.licitacion_id,
    l.nombre,
    1 - (le.vector <=> :query_vector) AS similarity,
    latest_cls.category_id,
    latest_cls.subcategory_id
FROM latest_embeddings le
JOIN core.licitacion l ON l.id = le.licitacion_id
LEFT JOIN LATERAL (
    SELECT category_id, subcategory_id FROM knowledge.classifications
    WHERE licitacion_id = le.licitacion_id
    ORDER BY created_at DESC LIMIT 1
) latest_cls ON true
WHERE (CAST(:exclude_licitacion_id AS INTEGER) IS NULL OR le.licitacion_id <> :exclude_licitacion_id)
  AND (1 - (le.vector <=> :query_vector)) >= :min_similarity
  AND (
        CAST(:category_code AS VARCHAR) IS NULL
        OR latest_cls.category_id IN (SELECT id FROM knowledge.categories WHERE code = :category_code)
      )
ORDER BY le.vector <=> :query_vector
LIMIT :top_k
"""


def _to_pgvector_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector.tolist()) + "]"


@dataclass(frozen=True, slots=True)
class SimilarLicitacion:
    licitacion_id: int
    nombre: str | None
    similarity: float
    category_id: int | None
    subcategory_id: int | None


class VectorSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_by_vector(
        self,
        vector: np.ndarray,
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
        exclude_licitacion_id: int | None = None,
        category_code: str | None = None,
    ) -> list[SimilarLicitacion]:
        result = await self._session.execute(
            text(_SEARCH_SQL),
            {
                "query_vector": _to_pgvector_literal(vector),
                "top_k": top_k,
                "min_similarity": min_similarity,
                "exclude_licitacion_id": exclude_licitacion_id,
                "category_code": category_code,
            },
        )
        return [
            SimilarLicitacion(
                licitacion_id=row.licitacion_id, nombre=row.nombre, similarity=float(row.similarity),
                category_id=row.category_id, subcategory_id=row.subcategory_id,
            )
            for row in result.all()
        ]

    async def find_similar_to_licitacion(
        self, licitacion_id: int, *, top_k: int = 10, min_similarity: float = 0.0,
    ) -> list[SimilarLicitacion]:
        row = (
            await self._session.execute(
                text(
                    "SELECT vector FROM knowledge.embeddings WHERE licitacion_id = :licitacion_id "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"licitacion_id": licitacion_id},
            )
        ).first()
        if row is None:
            return []
        vector = np.array(_parse_pgvector(row.vector), dtype=np.float32)
        return await self.search_by_vector(
            vector, top_k=top_k, min_similarity=min_similarity, exclude_licitacion_id=licitacion_id,
        )

    async def search_by_concept(
        self,
        concept_code: str,
        concept_vectors: tuple[ConceptVector, ...],
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[SimilarLicitacion]:
        node = next(candidate for candidate in concept_vectors if candidate.concept.code == concept_code)
        return await self.search_by_vector(node.vector, top_k=top_k, min_similarity=min_similarity)

    async def search_by_category(
        self,
        category_code: str,
        category_vectors: tuple[CategoryVector, ...],
        *,
        top_k: int = 10,
        min_similarity: float = 0.0,
    ) -> list[SimilarLicitacion]:
        node = next(candidate for candidate in category_vectors if candidate.category_code == category_code)
        return await self.search_by_vector(node.vector, top_k=top_k, min_similarity=min_similarity)


def _parse_pgvector(value: object) -> list[float]:
    """psycopg returns pgvector columns as their string literal ("[0.1,0.2,...]")
    unless the pgvector Python adapter is registered — parse it directly to
    avoid taking that extra dependency for a single read path."""
    if isinstance(value, str):
        return [float(component) for component in value.strip("[]").split(",")]
    return list(value)
