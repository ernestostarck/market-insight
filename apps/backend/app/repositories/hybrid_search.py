"""PostgreSQL full-text search over licitaciones/items (Fase 6.10).

Async, `AsyncSession` — same style as `VectorSearchRepository`
(app/repositories/vector_search.py) and `AnalyticsRepository` — raw SQL
via `text()` for `to_tsquery`/`ts_rank` (SQLAlchemy's expression language
covers `tsvector` reasonably, but staying consistent with how the rest of
this NLP search layer already writes its SQL keeps the querying style
uniform across app/repositories/vector_search.py and this file).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class TextMatch:
    licitacion_id: int
    nombre: str | None
    codigo: str | None
    rank: float


_FULLTEXT_SQL = """
SELECT id AS licitacion_id, nombre, codigo,
       ts_rank(search_vector, plainto_tsquery('spanish', :query)) AS rank
FROM core.licitacion
WHERE search_vector @@ plainto_tsquery('spanish', :query)
ORDER BY rank DESC
LIMIT :limit
"""

_PRODUCTS_SQL = """
SELECT l.id AS licitacion_id, l.nombre, l.codigo,
       MAX(ts_rank(i.search_vector, plainto_tsquery('spanish', :query))) AS rank
FROM core.licitacion_item i
JOIN core.licitacion l ON l.id = i.licitacion_id
WHERE i.search_vector @@ plainto_tsquery('spanish', :query)
GROUP BY l.id, l.nombre, l.codigo
ORDER BY rank DESC
LIMIT :limit
"""

_BY_CODE_SQL = """
SELECT id AS licitacion_id, nombre, codigo,
       CASE WHEN codigo = :code THEN 1.0 ELSE 0.5 END AS rank
FROM core.licitacion
WHERE codigo = :code OR codigo ILIKE :prefix
ORDER BY rank DESC, codigo ASC
LIMIT :limit
"""


class HybridSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_fulltext(self, query: str, *, limit: int = 20) -> list[TextMatch]:
        result = await self._session.execute(text(_FULLTEXT_SQL), {"query": query, "limit": limit})
        return [_to_match(row) for row in result.all()]

    async def search_products(self, query: str, *, limit: int = 20) -> list[TextMatch]:
        result = await self._session.execute(text(_PRODUCTS_SQL), {"query": query, "limit": limit})
        return [_to_match(row) for row in result.all()]

    async def search_by_code(self, code: str, *, limit: int = 20) -> list[TextMatch]:
        result = await self._session.execute(
            text(_BY_CODE_SQL), {"code": code, "prefix": f"{code}%", "limit": limit},
        )
        return [_to_match(row) for row in result.all()]


def _to_match(row) -> TextMatch:
    return TextMatch(licitacion_id=row.licitacion_id, nombre=row.nombre, codigo=row.codigo, rank=float(row.rank))
