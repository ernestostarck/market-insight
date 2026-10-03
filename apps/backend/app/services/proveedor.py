import uuid

from app.repositories.proveedor import ProveedorRepository
from app.schemas.proveedor import ProveedorCreate


class ProveedorService:
    def __init__(self, repository: ProveedorRepository):
        self.repository = repository

    async def get(self, proveedor_id: uuid.UUID):
        return await self.repository.get(proveedor_id)

    async def get_with_stats(self, proveedor_id: int):
        return await self.repository.get_with_stats(proveedor_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        q: str | None = None,
        region: str | None = None,
        rubro: str | None = None,
        tasa_minima: float | None = None,
        licitacion_ids: list[int] | None = None,
    ):
        # Always joined with stats (participaciones, adjudicaciones, tasa_exito,
        # categoria_principal), filtered or not, so the list always shows real numbers.
        return await self.repository.get_page_filtered(
            limit=limit,
            anchor_id=anchor_id,
            direction=direction,
            q=q,
            region=region,
            rubro=rubro,
            tasa_minima=tasa_minima,
            licitacion_ids=licitacion_ids,
        )

    async def ranking(self, **kwargs):
        return await self.repository.get_ranking(**kwargs)

    async def categoria_facets(self, *, licitacion_ids: list[int] | None = None):
        return await self.repository.categoria_facets(licitacion_ids=licitacion_ids)

    async def create(self, payload: ProveedorCreate):
        return await self.repository.create(payload)
