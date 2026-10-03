import uuid
from app.repositories.comprador import CompradorRepository
from app.schemas.comprador import CompradorCreate


class CompradorService:
    def __init__(self, repository: CompradorRepository):
        self.repository = repository

    async def get(self, comprador_id: uuid.UUID):
        return await self.repository.get(comprador_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(self, *, limit: int, anchor_id: int | None = None, direction: str = "next"):
        return await self.repository.get_page(limit=limit, anchor_id=anchor_id, direction=direction)

    async def create(self, payload: CompradorCreate):
        return await self.repository.create(payload)
