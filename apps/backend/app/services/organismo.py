import uuid
from app.repositories.organismo import OrganismoRepository
from app.schemas.organismo import OrganismoCreate


class OrganismoService:
    def __init__(self, repository: OrganismoRepository):
        self.repository = repository

    async def get(self, organismo_id: uuid.UUID):
        return await self.repository.get(organismo_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        licitacion_ids: list[int] | None = None,
    ):
        return await self.repository.get_page(
            limit=limit, anchor_id=anchor_id, direction=direction, licitacion_ids=licitacion_ids
        )

    async def ranking(self, **kwargs):
        return await self.repository.get_ranking(**kwargs)

    async def create(self, payload: OrganismoCreate):
        return await self.repository.create(payload)
