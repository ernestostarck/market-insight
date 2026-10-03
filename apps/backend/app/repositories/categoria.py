from __future__ import annotations

from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.categoria import Categoria
from app.models.core.licitacion import Adjudicacion, Licitacion
from app.models.core.organismo import Organismo
from app.models.core.proveedor import Proveedor
from app.nlp.segmento import id_in
from app.repositories.pagination import KeysetPage
from app.repositories.text_search import matches_text
from app.schemas.categoria import (
    Categoria as CategoriaSchema,
)
from app.schemas.categoria import (
    CategoriaOrganismoItem,
    CategoriaProveedorItem,
    split_rubro_breadcrumb,
)

_TOP_N = 5


class CategoriaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -- Award stats (licitaciones, monto, proveedores, organismos) --------------------
    #
    # `core.categoria` itself has no counters — these come from `core.licitacion`
    # (each tender's dominant rubro, set by CoreLicitacionItemLoader) and
    # `core.adjudicacion`, so listing or filtering by them needs the joins below.

    def _stats_statement(self):
        licitaciones_sq = (
            select(
                Licitacion.categoria_id.label("categoria_id"),
                func.count(func.distinct(Licitacion.id)).label("total"),
            )
            .where(Licitacion.categoria_id.isnot(None))
            .group_by(Licitacion.categoria_id)
            .subquery()
        )
        adjudicaciones_sq = (
            select(
                Licitacion.categoria_id.label("categoria_id"),
                func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto"),
                func.count(func.distinct(Adjudicacion.proveedor_id)).label("proveedores"),
            )
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .where(Licitacion.categoria_id.isnot(None))
            .group_by(Licitacion.categoria_id)
            .subquery()
        )
        organismos_sq = (
            select(
                Licitacion.categoria_id.label("categoria_id"),
                func.count(func.distinct(Licitacion.organismo_id)).label("total"),
            )
            .where(Licitacion.categoria_id.isnot(None))
            .group_by(Licitacion.categoria_id)
            .subquery()
        )

        monto_total = func.coalesce(adjudicaciones_sq.c.monto, 0)
        statement = (
            select(
                Categoria,
                func.coalesce(licitaciones_sq.c.total, 0).label("total_licitaciones"),
                monto_total.label("monto_total"),
                func.coalesce(adjudicaciones_sq.c.proveedores, 0).label("total_proveedores"),
                func.coalesce(organismos_sq.c.total, 0).label("total_organismos"),
            )
            .select_from(Categoria)
            .outerjoin(licitaciones_sq, licitaciones_sq.c.categoria_id == Categoria.id)
            .outerjoin(adjudicaciones_sq, adjudicaciones_sq.c.categoria_id == Categoria.id)
            .outerjoin(organismos_sq, organismos_sq.c.categoria_id == Categoria.id)
        )
        return statement, monto_total

    @staticmethod
    def _row_to_schema(row: Row[Any]) -> CategoriaSchema:
        categoria: Categoria = row.Categoria
        segmento, familia, clase = split_rubro_breadcrumb(categoria.nombre)
        return CategoriaSchema(
            id=categoria.id,
            codigo=categoria.codigo,
            nombre=categoria.nombre,
            segmento=segmento,
            familia=familia,
            clase=clase,
            total_licitaciones=row.total_licitaciones,
            monto_total=float(row.monto_total or 0),
            total_proveedores=row.total_proveedores,
            total_organismos=row.total_organismos,
        )

    async def get_with_stats(self, categoria_id: int) -> CategoriaSchema | None:
        statement, _monto_total = self._stats_statement()
        result = await self.session.execute(statement.where(Categoria.id == categoria_id))
        row = result.first()
        return self._row_to_schema(row) if row else None

    async def get_page_filtered(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        q: str | None = None,
        monto_minimo: float | None = None,
    ) -> KeysetPage[CategoriaSchema]:
        statement, monto_total = self._stats_statement()

        if q:
            statement = statement.where(matches_text(q, Categoria.codigo, Categoria.nombre))
        if monto_minimo is not None:
            statement = statement.where(monto_total >= monto_minimo)

        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))

        if anchor_id is not None:
            operator = Categoria.id > anchor_id if direction == "next" else Categoria.id < anchor_id
            statement = statement.where(operator)
        order = Categoria.id.asc() if direction == "next" else Categoria.id.desc()
        statement = statement.order_by(order).limit(limit + 1)

        result = await self.session.execute(statement)
        rows = list(result.all())
        has_more = len(rows) > limit
        items = [self._row_to_schema(row) for row in rows[:limit]]
        if direction == "previous":
            items.reverse()

        if direction == "next":
            has_previous = anchor_id is not None and bool(items)
            has_next = has_more
        else:
            has_previous = has_more
            has_next = bool(items)

        return KeysetPage(items=items, total=total or 0, has_next=has_next, has_previous=has_previous)

    _SORTABLE = ("monto_total", "total_licitaciones", "total_proveedores", "codigo", "nombre")

    async def get_ranking(
        self,
        *,
        limit: int,
        offset: int = 0,
        sort_by: str = "monto_total",
        sort_dir: str = "desc",
        q: str | None = None,
        monto_minimo: float | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> tuple[list[CategoriaSchema], int]:
        """Server-sorted, offset-paginated rubros (e.g. the top 10 by awarded amount)."""
        if sort_by not in self._SORTABLE:
            raise ValueError(f"sort_by must be one of {self._SORTABLE}")
        statement, monto_total = self._stats_statement()
        if licitacion_ids is not None:
            # Rubros of the segment's licitaciones.
            statement = statement.where(
                Categoria.id.in_(
                    select(Licitacion.categoria_id).where(id_in(Licitacion.id, licitacion_ids))
                )
            )
        if q:
            statement = statement.where(matches_text(q, Categoria.codigo, Categoria.nombre))
        if monto_minimo is not None:
            statement = statement.where(monto_total >= monto_minimo)

        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))
        column = (
            getattr(Categoria, sort_by)
            if sort_by in ("codigo", "nombre")
            else getattr(statement.selected_columns, sort_by)
        )
        order = column.asc().nulls_last() if sort_dir == "asc" else column.desc().nulls_last()
        result = await self.session.execute(
            statement.order_by(order, Categoria.id.asc()).offset(offset).limit(limit)
        )
        return [self._row_to_schema(row) for row in result.all()], total or 0

    # -- Top suppliers / buyers for a categoria's detail view ---------------------------

    async def get_top_proveedores(self, categoria_id: int, limit: int = _TOP_N) -> list[CategoriaProveedorItem]:
        monto = func.sum(Adjudicacion.monto_adjudicado)
        statement = (
            select(Proveedor.id, Proveedor.razon_social, Proveedor.rut, monto.label("monto"))
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .join(Proveedor, Proveedor.id == Adjudicacion.proveedor_id)
            .where(Licitacion.categoria_id == categoria_id)
            .group_by(Proveedor.id, Proveedor.razon_social, Proveedor.rut)
            .order_by(monto.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        total = sum(float(row.monto or 0) for row in rows)
        return [
            CategoriaProveedorItem(
                proveedor_id=row.id,
                proveedor_nombre=row.razon_social,
                proveedor_rut=row.rut,
                monto_adjudicado=float(row.monto or 0),
                cuota=round(float(row.monto or 0) / total * 100, 1) if total > 0 else 0.0,
            )
            for row in rows
        ]

    async def get_top_organismos(self, categoria_id: int, limit: int = _TOP_N) -> list[CategoriaOrganismoItem]:
        monto = func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0)
        statement = (
            select(
                Organismo.id, Organismo.nombre,
                monto.label("monto"),
                func.count(func.distinct(Licitacion.id)).label("total_licitaciones"),
            )
            .select_from(Licitacion)
            .join(Organismo, Organismo.id == Licitacion.organismo_id)
            .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
            .where(Licitacion.categoria_id == categoria_id)
            .group_by(Organismo.id, Organismo.nombre)
            .order_by(monto.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            CategoriaOrganismoItem(
                organismo_id=row.id,
                organismo_nombre=row.nombre,
                monto_comprado=float(row.monto or 0),
                total_licitaciones=row.total_licitaciones,
            )
            for row in rows
        ]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
