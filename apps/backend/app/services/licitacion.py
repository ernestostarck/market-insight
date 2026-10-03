import uuid
from app.repositories.licitacion import LicitacionRepository
from app.schemas.licitacion import LicitacionCreate


class LicitacionService:
    def __init__(self, repository: LicitacionRepository):
        self.repository = repository

    async def get(self, licitacion_id: uuid.UUID):
        return await self.repository.get(licitacion_id)

    async def list(self, skip: int = 0, limit: int = 100):
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def page(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        q: str | None = None,
        estado: str | None = None,
        organismo_id: int | None = None,
        monto_min: float | None = None,
        monto_max: float | None = None,
        licitacion_ids: list[int] | None = None,
    ):
        return await self.repository.get_page_filtered(
            limit=limit,
            anchor_id=anchor_id,
            direction=direction,
            q=q,
            estado=estado,
            organismo_id=organismo_id,
            monto_min=monto_min,
            monto_max=monto_max,
            licitacion_ids=licitacion_ids,
        )

    async def create(self, payload: LicitacionCreate):
        return await self.repository.create(payload)
