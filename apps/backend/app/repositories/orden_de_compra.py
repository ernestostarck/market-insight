from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orden_de_compra import OrdenDeCompra
from app.repositories.pagination import KeysetPage, fetch_keyset_page
from app.schemas.orden_de_compra import OrdenDeCompraCreate


class OrdenDeCompraRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, orden_de_compra_id: int) -> OrdenDeCompra | None:
        result = await self.session.execute(
            select(OrdenDeCompra).where(OrdenDeCompra.id == orden_de_compra_id)
        )
        return result.scalars().first()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[OrdenDeCompra]:
        result = await self.session.execute(
            select(OrdenDeCompra).order_by(OrdenDeCompra.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_page(
        self, *, limit: int, anchor_id: int | None = None, direction: str = "next"
    ) -> KeysetPage[OrdenDeCompra]:
        return await fetch_keyset_page(
            self.session, OrdenDeCompra, limit=limit, anchor_id=anchor_id, direction=direction
        )

    async def create(self, payload: OrdenDeCompraCreate) -> OrdenDeCompra:
        db_obj = OrdenDeCompra(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
