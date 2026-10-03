import uuid
from app.repositories.contrato import ContratoRepository
from app.schemas.contrato import ContratoCreate


class ContratoService:
    def __init__(self, repository: ContratoRepository):
        self.repository = repository

    async def get(self, contrato_id: uuid.UUID):
        return await self.repository.get(contrato_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(self, *, limit: int, anchor_id: int | None = None, direction: str = "next"):
        return await self.repository.get_page(limit=limit, anchor_id=anchor_id, direction=direction)

    async def create(self, payload: ContratoCreate):
        return await self.repository.create(payload)
