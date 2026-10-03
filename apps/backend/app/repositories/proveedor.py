from __future__ import annotations

from typing import Any

from sqlalchemy import Row, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.categoria import Categoria
from app.models.core.licitacion import Adjudicacion, Licitacion, Oferta
from app.models.core.proveedor import Proveedor
from app.nlp.segmento import id_in
from app.repositories.pagination import KeysetPage
from app.repositories.text_search import matches_text
from app.schemas.proveedor import Proveedor as ProveedorSchema
from app.schemas.proveedor import ProveedorCreate


class ProveedorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, proveedor_id: int) -> Proveedor | None:
        result = await self.session.execute(
            select(Proveedor).where(Proveedor.id == proveedor_id)
        )
        return result.scalars().first()

    async def get_by_rut(self, rut: str) -> Proveedor | None:
        result = await self.session.execute(
            select(Proveedor).where(Proveedor.rut == rut)
        )
        return result.scalars().first()

    async def search_by_razon_social(
        self, razon_social: str, skip: int = 0, limit: int = 100
    ) -> list[Proveedor]:
        result = await self.session.execute(
            select(Proveedor)
            .where(
                Proveedor.razon_social.ilike(
                    f"%{_escape_like(razon_social)}%", escape="\\"
                )
            )
            .order_by(Proveedor.razon_social.asc(), Proveedor.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[Proveedor]:
        result = await self.session.execute(
            select(Proveedor).order_by(Proveedor.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, payload: ProveedorCreate) -> Proveedor:
        db_obj = Proveedor(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    # -- Performance stats (participation, awards, success rate, main category) --------
    #
    # These come from `core.oferta` / `core.adjudicacion`, not from a column on
    # `core.proveedor`, so listing or filtering by them needs the aggregate joins below.

    def _stats_statement(self):
        """Base SELECT: one row per proveedor, joined with its aggregated stats.

        No filter, ordering or pagination applied yet — callers add those.
        Returns the statement plus the two computed columns filters need directly
        (they live in subqueries, so they aren't reachable from `Proveedor` alone).
        """
        participaciones_sq = (
            select(
                Oferta.proveedor_id.label("proveedor_id"),
                func.count(func.distinct(Oferta.id)).label("total"),
            )
            .group_by(Oferta.proveedor_id)
            .subquery()
        )
        adjudicaciones_sq = (
            select(
                Adjudicacion.proveedor_id.label("proveedor_id"),
                func.count(func.distinct(Adjudicacion.id)).label("total"),
                func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto"),
            )
            .group_by(Adjudicacion.proveedor_id)
            .subquery()
        )
        # "Main" category: the one the proveedor has been awarded in most often.
        categoria_counts_sq = (
            select(
                Adjudicacion.proveedor_id.label("proveedor_id"),
                Categoria.nombre.label("nombre"),
                func.count().label("cnt"),
            )
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .join(Categoria, Categoria.id == Licitacion.categoria_id)
            .group_by(Adjudicacion.proveedor_id, Categoria.nombre)
            .subquery()
        )
        categoria_ranked_sq = select(
            categoria_counts_sq.c.proveedor_id,
            categoria_counts_sq.c.nombre,
            func.row_number()
            .over(
                partition_by=categoria_counts_sq.c.proveedor_id,
                order_by=categoria_counts_sq.c.cnt.desc(),
            )
            .label("rn"),
        ).subquery()
        categoria_principal_sq = (
            select(categoria_ranked_sq.c.proveedor_id, categoria_ranked_sq.c.nombre)
            .where(categoria_ranked_sq.c.rn == 1)
            .subquery()
        )

        participaciones = func.coalesce(participaciones_sq.c.total, 0)
        adjudicaciones = func.coalesce(adjudicaciones_sq.c.total, 0)
        tasa_exito = case(
            (participaciones > 0, adjudicaciones * 100.0 / participaciones),
            else_=None,
        )

        statement = (
            select(
                Proveedor,
                participaciones.label("total_licitaciones_participadas"),
                adjudicaciones.label("total_adjudicaciones"),
                func.coalesce(adjudicaciones_sq.c.monto, 0).label("monto_total_adjudicado"),
                tasa_exito.label("tasa_exito"),
                categoria_principal_sq.c.nombre.label("categoria_principal"),
            )
            .select_from(Proveedor)
            .outerjoin(participaciones_sq, participaciones_sq.c.proveedor_id == Proveedor.id)
            .outerjoin(adjudicaciones_sq, adjudicaciones_sq.c.proveedor_id == Proveedor.id)
            .outerjoin(
                categoria_principal_sq, categoria_principal_sq.c.proveedor_id == Proveedor.id
            )
        )
        return statement, tasa_exito, categoria_principal_sq.c.nombre

    @staticmethod
    def _row_to_schema(row: Row[Any]) -> ProveedorSchema:
        proveedor: Proveedor = row.Proveedor
        return ProveedorSchema(
            id=proveedor.id,
            rut=proveedor.rut,
            razon_social=proveedor.razon_social,
            nombre_fantasia=proveedor.nombre_fantasia,
            region=proveedor.region,
            categoria_principal=row.categoria_principal,
            fecha_registro=proveedor.created_at,
            total_licitaciones_participadas=row.total_licitaciones_participadas,
            total_adjudicaciones=row.total_adjudicaciones,
            tasa_exito=float(row.tasa_exito) if row.tasa_exito is not None else None,
            monto_total_adjudicado=float(row.monto_total_adjudicado or 0),
        )

    async def get_with_stats(self, proveedor_id: int) -> ProveedorSchema | None:
        """Same shape as `get_page_filtered` items, for a single proveedor."""
        statement, _tasa_exito, _categoria_principal = self._stats_statement()
        result = await self.session.execute(statement.where(Proveedor.id == proveedor_id))
        row = result.first()
        return self._row_to_schema(row) if row else None

    async def get_page_filtered(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        q: str | None = None,
        region: str | None = None,
        rubro: str | None = None,
        tasa_minima: float | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> KeysetPage[ProveedorSchema]:
        """Keyset page over proveedores, filtered by search/region/rubro/tasa_minima.

        `rubro` and `tasa_minima` filter on the aggregated stats (main award category,
        success rate), computed in `_stats_statement`, not on a plain column.
        """
        statement, tasa_exito, categoria_principal = self._stats_statement()
        statement = self._apply_filters(
            statement,
            tasa_exito,
            categoria_principal,
            q=q,
            region=region,
            rubro=rubro,
            tasa_minima=tasa_minima,
            licitacion_ids=licitacion_ids,
        )

        total = await self.session.scalar(
            select(func.count()).select_from(statement.subquery())
        )

        if anchor_id is not None:
            operator = Proveedor.id > anchor_id if direction == "next" else Proveedor.id < anchor_id
            statement = statement.where(operator)
        order = Proveedor.id.asc() if direction == "next" else Proveedor.id.desc()
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


    _SORTABLE = ("monto_total_adjudicado", "total_adjudicaciones", "tasa_exito", "razon_social")

    async def get_ranking(
        self,
        *,
        limit: int,
        offset: int = 0,
        sort_by: str = "monto_total_adjudicado",
        sort_dir: str = "desc",
        q: str | None = None,
        rubro: str | None = None,
        tasa_minima: float | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> tuple[list[ProveedorSchema], int]:
        """Server-sorted, offset-paginated proveedores (e.g. the top 10 by awarded amount)."""
        if sort_by not in self._SORTABLE:
            raise ValueError(f"sort_by must be one of {self._SORTABLE}")
        statement, tasa_exito, categoria_principal = self._stats_statement()
        statement = self._apply_filters(
            statement,
            tasa_exito,
            categoria_principal,
            q=q,
            rubro=rubro,
            tasa_minima=tasa_minima,
            licitacion_ids=licitacion_ids,
        )
        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))

        column = (
            Proveedor.razon_social
            if sort_by == "razon_social"
            else getattr(statement.selected_columns, sort_by)
        )
        order = column.asc().nulls_last() if sort_dir == "asc" else column.desc().nulls_last()
        result = await self.session.execute(
            statement.order_by(order, Proveedor.id.asc()).offset(offset).limit(limit)
        )
        return [self._row_to_schema(row) for row in result.all()], total or 0

    async def categoria_facets(
        self, *, licitacion_ids: list[int] | None = None, limit: int = 40
    ) -> list[tuple[str, int]]:
        """Most common main award categories among proveedores, for the rubro filter."""
        statement, tasa_exito, categoria_principal = self._stats_statement()
        statement = self._apply_filters(
            statement, tasa_exito, categoria_principal, licitacion_ids=licitacion_ids
        )
        sub = statement.subquery()
        result = await self.session.execute(
            select(sub.c.categoria_principal, func.count())
            .where(sub.c.categoria_principal.isnot(None))
            .group_by(sub.c.categoria_principal)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(nombre, count) for nombre, count in result.all()]

    @staticmethod
    def _apply_filters(
        statement,
        tasa_exito,
        categoria_principal,
        *,
        q: str | None = None,
        region: str | None = None,
        rubro: str | None = None,
        tasa_minima: float | None = None,
        licitacion_ids: list[int] | None = None,
    ):
        if licitacion_ids is not None:
            # Suppliers with at least one award in the segment's licitaciones.
            statement = statement.where(
                Proveedor.id.in_(
                    select(Adjudicacion.proveedor_id).where(
                        id_in(Adjudicacion.licitacion_id, licitacion_ids)
                    )
                )
            )
        if q:
            statement = statement.where(
                matches_text(q, Proveedor.rut, Proveedor.razon_social, Proveedor.nombre_fantasia)
            )
        if region:
            statement = statement.where(Proveedor.region == region)
        if rubro:
            statement = statement.where(categoria_principal == rubro)
        if tasa_minima is not None:
            # NULL (no participations yet) correctly fails this comparison.
            statement = statement.where(tasa_exito >= tasa_minima)
        return statement


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
