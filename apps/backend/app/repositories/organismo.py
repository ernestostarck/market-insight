from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.categoria import Categoria
from app.models.core.licitacion import Adjudicacion, Licitacion
from app.models.core.organismo import Organismo
from app.nlp.segmento import id_in
from app.repositories.pagination import KeysetPage, fetch_keyset_page
from app.repositories.text_search import matches_text
from app.schemas.organismo import OrganismoCreate, OrganismoRanking


class OrganismoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, organismo_id: int) -> Organismo | None:
        result = await self.session.execute(
            select(Organismo).where(Organismo.id == organismo_id)
        )
        return result.scalars().first()

    async def search_by_nombre(
        self, nombre: str, skip: int = 0, limit: int = 100
    ) -> list[Organismo]:
        result = await self.session.execute(
            select(Organismo)
            .where(
                Organismo.nombre.ilike(f"%{_escape_like(nombre)}%", escape="\\")
            )
            .order_by(Organismo.nombre.asc(), Organismo.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[Organismo]:
        result = await self.session.execute(
            select(Organismo).order_by(Organismo.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_page(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        licitacion_ids: list[int] | None = None,
    ) -> KeysetPage[Organismo]:
        where = None
        if licitacion_ids is not None:
            # Agencies that published at least one of the segment's licitaciones.
            where = Organismo.id.in_(
                select(Licitacion.organismo_id).where(id_in(Licitacion.id, licitacion_ids))
            )
        return await fetch_keyset_page(
            self.session,
            Organismo,
            limit=limit,
            anchor_id=anchor_id,
            direction=direction,
            where=where,
        )

    _SORTABLE = ("monto_total_comprado", "total_licitaciones", "licitaciones_activas", "nombre")

    async def get_ranking(
        self,
        *,
        limit: int,
        offset: int = 0,
        sort_by: str = "monto_total_comprado",
        sort_dir: str = "desc",
        q: str | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> tuple[list[OrganismoRanking], int]:
        """Server-sorted, offset-paginated agencies with their purchasing stats."""
        if sort_by not in self._SORTABLE:
            raise ValueError(f"sort_by must be one of {self._SORTABLE}")

        # Aggregates are restricted to the segment's licitaciones when one is selected.
        scope = id_in(Licitacion.id, licitacion_ids) if licitacion_ids is not None else None

        licitaciones_sq = select(
            Licitacion.organismo_id.label("organismo_id"),
            func.count(Licitacion.id).label("total"),
            func.count(Licitacion.id).filter(Licitacion.estado.in_(_ESTADO_PUBLICADA)).label("activas"),
        ).group_by(Licitacion.organismo_id)
        monto_sq = (
            select(
                Licitacion.organismo_id.label("organismo_id"),
                func.sum(Adjudicacion.monto_adjudicado).label("monto"),
            )
            .join(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
            .group_by(Licitacion.organismo_id)
        )
        categoria_counts = (
            select(
                Licitacion.organismo_id.label("organismo_id"),
                Categoria.nombre.label("nombre"),
                func.row_number()
                .over(partition_by=Licitacion.organismo_id, order_by=func.count().desc())
                .label("rn"),
            )
            .join(Categoria, Categoria.id == Licitacion.categoria_id)
            .group_by(Licitacion.organismo_id, Categoria.nombre)
        )
        if scope is not None:
            licitaciones_sq = licitaciones_sq.where(scope)
            monto_sq = monto_sq.where(scope)
            categoria_counts = categoria_counts.where(scope)
        licitaciones_sq = licitaciones_sq.subquery()
        monto_sq = monto_sq.subquery()
        categoria_counts = categoria_counts.subquery()

        total_licitaciones = func.coalesce(licitaciones_sq.c.total, 0).label("total_licitaciones")
        activas = func.coalesce(licitaciones_sq.c.activas, 0).label("licitaciones_activas")
        monto = func.coalesce(monto_sq.c.monto, 0).label("monto_total_comprado")
        statement = (
            select(Organismo, total_licitaciones, activas, monto, categoria_counts.c.nombre.label("categoria_principal"))
            .outerjoin(licitaciones_sq, licitaciones_sq.c.organismo_id == Organismo.id)
            .outerjoin(monto_sq, monto_sq.c.organismo_id == Organismo.id)
            .outerjoin(
                categoria_counts,
                (categoria_counts.c.organismo_id == Organismo.id) & (categoria_counts.c.rn == 1),
            )
        )
        if scope is not None:
            statement = statement.where(licitaciones_sq.c.total.isnot(None))
        if q:
            statement = statement.where(matches_text(q, Organismo.nombre, Organismo.codigo))

        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))
        column = {
            "monto_total_comprado": monto,
            "total_licitaciones": total_licitaciones,
            "licitaciones_activas": activas,
            "nombre": Organismo.nombre,
        }[sort_by]
        order = column.asc().nulls_last() if sort_dir == "asc" else column.desc().nulls_last()
        result = await self.session.execute(
            statement.order_by(order, Organismo.id.asc()).offset(offset).limit(limit)
        )
        items = [
            OrganismoRanking(
                id=row.Organismo.id,
                codigo=row.Organismo.codigo,
                nombre=row.Organismo.nombre,
                total_licitaciones=row.total_licitaciones,
                licitaciones_activas=row.licitaciones_activas,
                monto_total_comprado=float(row.monto_total_comprado or 0),
                categoria_principal=row.categoria_principal,
            )
            for row in result.all()
        ]
        return items, total or 0

    async def create(self, payload: OrganismoCreate) -> Organismo:
        db_obj = Organismo(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj


# ChileCompra CodigoEstado for an open ("publicada") licitacion; the label form is
# accepted too in case a loader normalised it.
_ESTADO_PUBLICADA = ("5", "publicada")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
