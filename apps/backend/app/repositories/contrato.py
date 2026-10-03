from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contrato import Contrato
from app.repositories.pagination import KeysetPage, fetch_keyset_page
from app.schemas.contrato import ContratoCreate


class ContratoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, contrato_id: int) -> Contrato | None:
        result = await self.session.execute(
            select(Contrato).where(Contrato.id == contrato_id)
        )
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[Contrato]:
        result = await self.session.execute(
            select(Contrato).order_by(Contrato.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_page(
        self, *, limit: int, anchor_id: int | None = None, direction: str = "next"
    ) -> KeysetPage[Contrato]:
        return await fetch_keyset_page(
            self.session, Contrato, limit=limit, anchor_id=anchor_id, direction=direction
        )

    async def create(self, payload: ContratoCreate) -> Contrato:
        db_obj = Contrato(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
