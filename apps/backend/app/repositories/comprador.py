from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comprador import Comprador
from app.repositories.pagination import KeysetPage, fetch_keyset_page
from app.schemas.comprador import CompradorCreate


class CompradorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, comprador_id: int) -> Comprador | None:
        result = await self.session.execute(
            select(Comprador).where(Comprador.id == comprador_id)
        )
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[Comprador]:
        result = await self.session.execute(
            select(Comprador).order_by(Comprador.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_page(
        self, *, limit: int, anchor_id: int | None = None, direction: str = "next"
    ) -> KeysetPage[Comprador]:
        return await fetch_keyset_page(
            self.session, Comprador, limit=limit, anchor_id=anchor_id, direction=direction
        )

    async def create(self, payload: CompradorCreate) -> Comprador:
        db_obj = Comprador(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
