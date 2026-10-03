"""Federated search over canonical procurement entities."""

from __future__ import annotations

import asyncio

from app.repositories.licitacion import LicitacionRepository
from app.repositories.organismo import OrganismoRepository
from app.repositories.proveedor import ProveedorRepository
from app.schemas.search import SearchEntity, SearchQuery, SearchResponse, SearchResult


class SearchService:
    """Search canonical entities concurrently and return a uniform result shape."""

    def __init__(
        self,
        licitacion_repository: LicitacionRepository,
        proveedor_repository: ProveedorRepository,
        organismo_repository: OrganismoRepository,
    ) -> None:
        self._licitaciones = licitacion_repository
        self._proveedores = proveedor_repository
        self._organismos = organismo_repository

    async def search(self, request: SearchQuery) -> SearchResponse:
        tasks: dict[SearchEntity, object] = {}
        if "licitacion" in request.entities:
            tasks["licitacion"] = self._licitaciones.search_by_text(
                request.query, limit=request.limit_per_entity
            )
        if "proveedor" in request.entities:
            tasks["proveedor"] = self._proveedores.search_by_razon_social(
                request.query, limit=request.limit_per_entity
            )
        if "organismo" in request.entities:
            tasks["organismo"] = self._organismos.search_by_nombre(
                request.query, limit=request.limit_per_entity
            )

        entity_types = list(tasks)
        rows_by_entity = await asyncio.gather(*tasks.values())
        results: list[SearchResult] = []
        for entity_type, rows in zip(entity_types, rows_by_entity, strict=True):
            results.extend(self._to_result(entity_type, row) for row in rows)

        results.sort(key=lambda item: (item.entity_type, item.title.casefold(), item.id))
        return SearchResponse(
            query=request.query,
            entities=sorted(request.entities),
            total=len(results),
            results=results,
        )

    @staticmethod
    def _to_result(entity_type: SearchEntity, row: object) -> SearchResult:
        if entity_type == "licitacion":
            return SearchResult(
                entity_type=entity_type,
                id=row.id,
                title=row.nombre or row.codigo or f"Licitación {row.id}",
                subtitle=row.estado,
                code=row.codigo,
                metadata={
                    "organismo_id": row.organismo_id,
                    "monto_estimado": float(row.monto_estimado)
                    if row.monto_estimado is not None
                    else None,
                    "es_adjudicada": row.es_adjudicada,
                },
            )
        if entity_type == "proveedor":
            return SearchResult(
                entity_type=entity_type,
                id=row.id,
                title=row.razon_social or row.nombre_fantasia or f"Proveedor {row.id}",
                subtitle=row.rut,
                code=row.rut,
                metadata={"region": row.region, "estado": row.estado},
            )
        return SearchResult(
            entity_type=entity_type,
            id=row.id,
            title=row.nombre or row.codigo or f"Organismo {row.id}",
            subtitle=row.region,
            code=row.codigo,
            metadata={"comuna": row.comuna, "tipo": row.tipo},
        )
