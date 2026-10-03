import uuid
from app.repositories.orden_de_compra import OrdenDeCompraRepository
from app.schemas.orden_de_compra import OrdenDeCompraCreate


class OrdenDeCompraService:
    def __init__(self, repository: OrdenDeCompraRepository):
        self.repository = repository

    async def get(self, orden_de_compra_id: uuid.UUID):
        return await self.repository.get(orden_de_compra_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(self, *, limit: int, anchor_id: int | None = None, direction: str = "next"):
        return await self.repository.get_page(limit=limit, anchor_id=anchor_id, direction=direction)

    async def create(self, payload: OrdenDeCompraCreate):
        return await self.repository.create(payload)
