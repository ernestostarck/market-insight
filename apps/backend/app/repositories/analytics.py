"""Read-only access to analytics aggregates.

market_monthly/supplier_performance/category_spending/disability_contracts
compute their aggregates directly from core.* (already populated by the
ChileCompra ETL). They do NOT read the dw.* star schema (dw.fact_*/dw.dim_*,
see app/models/marts.py): nothing in this codebase loads those tables, so
the mv_market_monthly/v_supplier_performance/etc. views are always empty.
Until a real dw loader exists, core.* is the source of truth.

`category_spending`'s `gasto_total_oc`/`numero_ordenes_compra`/`gasto_promedio_oc`
field names refer to purchase orders (their original dw source), but core.*
has no canonical purchase-order table either — they are populated from
`core.adjudicacion` (awarded amount) instead, the closest real proxy. Field
names are kept as-is because app/ai/sql_retriever.py's text-to-SQL prompts
describe this exact schema; only the data source changed.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

from sqlalchemy import ColumnElement, Date, Row, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adjudicacion_analytics_snapshot import AdjudicacionAnalyticsSnapshot
from app.models.core.categoria import Categoria
from app.models.core.licitacion import Adjudicacion, Licitacion, LicitacionItem
from app.models.core.organismo import Organismo
from app.models.core.proveedor import Proveedor
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.segmento import id_in, terms_filter


@lru_cache(maxsize=1)
def _domain_dictionary_terms() -> tuple[str, ...]:
    """Real surface forms (term/synonym/abbreviation) from the versioned
    geriatría/discapacidad domain dictionary (app/nlp/dictionary.py) — used to
    scope "Mercado Objetivo" to this niche without depending on a pre-run NLP
    classification (only ~150 licitaciones have one so far)."""
    dictionary = load_initial_dictionary()
    forms = {
        form.strip().lower()
        for entry in dictionary.entries
        for form in entry.all_surface_forms()
        if form.strip()
    }
    return tuple(sorted(forms))


def _domain_niche_filter(terms: tuple[str, ...]) -> ColumnElement[bool]:
    return terms_filter(terms)
from app.models.marts import DQMissingKeys


class AnalyticsRepository:
    """Asynchronous, read-only repository for the published analytics layer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def market_monthly(
        self,
        *,
        start_month: date | None = None,
        end_month: date | None = None,
        licitacion_ids: list[int] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Row[Any]]:
        mes = func.date_trunc("month", Licitacion.fecha_publicacion).cast(Date).label("mes")
        statement = (
            select(
                mes,
                func.count(func.distinct(Licitacion.id)).label("total_licitaciones"),
                func.count(func.distinct(Adjudicacion.id)).label("total_adjudicaciones"),
                func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label(
                    "monto_total_adjudicado"
                ),
            )
            .select_from(Licitacion)
            .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
            .where(Licitacion.fecha_publicacion.isnot(None))
            .group_by(mes)
        )
        if licitacion_ids is not None:
            statement = statement.where(id_in(Licitacion.id, licitacion_ids))
        if start_month is not None:
            statement = statement.having(mes >= start_month)
        if end_month is not None:
            statement = statement.having(mes <= end_month)
        return await self._rows(statement.order_by(mes.desc()), offset, limit)

    async def supplier_performance(
        self,
        *,
        query: str | None = None,
        min_awarded_amount: float | None = None,
        licitacion_ids: list[int] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Row[Any]]:
        monto_total = func.sum(Adjudicacion.monto_adjudicado).label("monto_total_adjudicado")
        statement = (
            select(
                Proveedor.razon_social,
                Proveedor.rut,
                func.count(func.distinct(Adjudicacion.id)).label("total_adjudicaciones"),
                monto_total,
                func.avg(Adjudicacion.ratio_adjudicacion).label("ratio_adjudicacion_promedio"),
                func.max(Adjudicacion.fecha_adjudicacion).label("ultima_adjudicacion"),
            )
            .select_from(Adjudicacion)
            .join(Proveedor, Proveedor.id == Adjudicacion.proveedor_id)
            .group_by(Proveedor.razon_social, Proveedor.rut)
        )
        if licitacion_ids is not None:
            statement = statement.where(id_in(Adjudicacion.licitacion_id, licitacion_ids))
        if query:
            statement = statement.where(Proveedor.razon_social.ilike(f"%{query.strip()}%"))
        if min_awarded_amount is not None:
            statement = statement.having(monto_total >= min_awarded_amount)
        return await self._rows(
            statement.order_by(monto_total.desc(), Proveedor.razon_social.asc()), offset, limit
        )

    async def category_spending(
        self,
        *,
        category_code: str | None = None,
        licitacion_ids: list[int] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Row[Any]]:
        gasto_total = func.sum(Adjudicacion.monto_adjudicado).label("gasto_total_oc")
        statement = (
            select(
                Categoria.nombre.label("categoria"),
                Categoria.codigo.label("codigo_categoria"),
                gasto_total,
                func.count(func.distinct(Adjudicacion.id)).label("numero_ordenes_compra"),
                func.avg(Adjudicacion.monto_adjudicado).label("gasto_promedio_oc"),
            )
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .join(Categoria, Categoria.id == Licitacion.categoria_id)
            .group_by(Categoria.nombre, Categoria.codigo)
        )
        if licitacion_ids is not None:
            statement = statement.where(id_in(Licitacion.id, licitacion_ids))
        if category_code:
            statement = statement.where(Categoria.codigo == category_code)
        return await self._rows(
            statement.order_by(gasto_total.desc(), Categoria.nombre.asc()), offset, limit
        )

    async def disability_contracts(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        organism: str | None = None,
        supplier: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Row[Any]]:
        periodo = func.date_trunc("month", Adjudicacion.fecha_adjudicacion).cast(Date).label("periodo")
        statement = (
            select(
                Licitacion.codigo.label("licitacion_id"),
                Licitacion.nombre,
                Licitacion.descripcion,
                Adjudicacion.monto_adjudicado,
                Proveedor.razon_social.label("proveedor"),
                Organismo.nombre.label("organismo"),
                periodo,
            )
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .join(Proveedor, Proveedor.id == Adjudicacion.proveedor_id)
            .join(Organismo, Organismo.id == Licitacion.organismo_id)
            .where(
                Licitacion.nombre.ilike("%discapacidad%")
                | Licitacion.descripcion.ilike("%discapacidad%")
                | Licitacion.nombre.ilike("%inclusi%")
                | Licitacion.descripcion.ilike("%inclusi%")
            )
        )
        if start_date is not None:
            statement = statement.where(Adjudicacion.fecha_adjudicacion >= start_date)
        if end_date is not None:
            statement = statement.where(Adjudicacion.fecha_adjudicacion <= end_date)
        if organism:
            statement = statement.where(Organismo.nombre.ilike(f"%{organism.strip()}%"))
        if supplier:
            statement = statement.where(Proveedor.razon_social.ilike(f"%{supplier.strip()}%"))
        return await self._rows(
            statement.order_by(periodo.desc(), Adjudicacion.monto_adjudicado.desc()),
            offset,
            limit,
        )

    async def market_objective_summary(
        self,
        *,
        terms: tuple[str, ...] | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Defaults to the geriatría/discapacidad niche; a segmento (see
        app/nlp/segmento.py) passes its own terms and pre-matched licitacion ids."""
        if terms is None:
            terms = _domain_dictionary_terms()
        if licitacion_ids is None:
            # Run the expensive ILIKE dictionary scan once and reuse the matching ids in every query below.
            licitacion_ids = list(
                (
                    await self._session.execute(
                        select(Licitacion.id).where(_domain_niche_filter(terms))
                    )
                ).scalars().all()
            )
        niche = id_in(Licitacion.id, licitacion_ids)

        kpi_row = (
            await self._session.execute(
                select(
                    func.count(func.distinct(Licitacion.id)).label("licitaciones"),
                    func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto_total"),
                    func.count(func.distinct(Adjudicacion.proveedor_id)).label("proveedores"),
                    func.count(func.distinct(Licitacion.organismo_id)).label("organismos"),
                    func.avg(Adjudicacion.monto_adjudicado).label("precio_promedio"),
                )
                .select_from(Licitacion)
                .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
                .where(niche)
            )
        ).one()

        mes = func.date_trunc("month", Licitacion.fecha_publicacion).cast(Date).label("mes")
        trend_rows = (
            await self._session.execute(
                select(
                    mes,
                    func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto"),
                    func.count(func.distinct(Licitacion.id)).label("licitaciones"),
                )
                .select_from(Licitacion)
                .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
                .where(niche, Licitacion.fecha_publicacion.isnot(None))
                .group_by(mes)
                .order_by(mes)
            )
        ).all()

        tasa_crecimiento = None
        if len(trend_rows) >= 2:
            prev_monto, last_monto = float(trend_rows[-2].monto), float(trend_rows[-1].monto)
            if prev_monto > 0:
                tasa_crecimiento = round((last_monto - prev_monto) / prev_monto * 100, 1)

        monto_org = func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto_total")
        organismo_rows = (
            await self._session.execute(
                select(
                    Organismo.nombre,
                    monto_org,
                    func.count(func.distinct(Licitacion.id)).label("contratos"),
                )
                .select_from(Licitacion)
                .join(Organismo, Organismo.id == Licitacion.organismo_id)
                .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
                .where(niche)
                .group_by(Organismo.nombre)
                .order_by(monto_org.desc())
                .limit(10)
            )
        ).all()
        total_organismo_monto = sum(float(r.monto_total) for r in organismo_rows)

        monto_prov = func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto_total")
        proveedor_rows = (
            await self._session.execute(
                select(
                    Proveedor.razon_social,
                    Proveedor.rut,
                    monto_prov,
                    func.count(func.distinct(Adjudicacion.id)).label("contratos"),
                )
                .select_from(Adjudicacion)
                .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
                .join(Proveedor, Proveedor.id == Adjudicacion.proveedor_id)
                .where(niche)
                .group_by(Proveedor.razon_social, Proveedor.rut)
                .order_by(monto_prov.desc())
                .limit(10)
            )
        ).all()
        total_proveedor_monto = sum(float(r.monto_total) for r in proveedor_rows)

        monto_cat = func.coalesce(func.sum(Adjudicacion.monto_adjudicado), 0).label("monto")
        categoria_rows = (
            await self._session.execute(
                select(Categoria.codigo, Categoria.nombre, monto_cat)
                .select_from(Licitacion)
                .join(Categoria, Categoria.id == Licitacion.categoria_id)
                .outerjoin(Adjudicacion, Adjudicacion.licitacion_id == Licitacion.id)
                .where(niche)
                .group_by(Categoria.codigo, Categoria.nombre)
                .order_by(monto_cat.desc())
                .limit(10)
            )
        ).all()
        total_categoria_monto = sum(float(r.monto) for r in categoria_rows)

        return {
            "kpis": {
                "licitaciones_relacionadas": kpi_row.licitaciones,
                "monto_total": float(kpi_row.monto_total or 0),
                "proveedores_activos": kpi_row.proveedores,
                "organismos_activos": kpi_row.organismos,
                "precio_promedio": (
                    float(kpi_row.precio_promedio) if kpi_row.precio_promedio is not None else None
                ),
            },
            "tasa_crecimiento": tasa_crecimiento,
            "tendencias": [
                {"mes": r.mes, "monto": float(r.monto), "licitaciones": r.licitaciones}
                for r in trend_rows
            ],
            "organismos_lideres": [
                {
                    "nombre": r.nombre,
                    "rut": None,
                    "monto_total": float(r.monto_total),
                    "porcentaje": (
                        round(float(r.monto_total) / total_organismo_monto * 100, 1)
                        if total_organismo_monto
                        else 0.0
                    ),
                    "contratos": r.contratos,
                }
                for r in organismo_rows
            ],
            "proveedores_lideres": [
                {
                    "nombre": r.razon_social,
                    "rut": r.rut,
                    "monto_total": float(r.monto_total),
                    "porcentaje": (
                        round(float(r.monto_total) / total_proveedor_monto * 100, 1)
                        if total_proveedor_monto
                        else 0.0
                    ),
                    "contratos": r.contratos,
                }
                for r in proveedor_rows
            ],
            "categorias_relacionadas": [
                {
                    "codigo": r.codigo,
                    "nombre": r.nombre,
                    "monto": float(r.monto),
                    "porcentaje": (
                        round(float(r.monto) / total_categoria_monto * 100, 1)
                        if total_categoria_monto
                        else 0.0
                    ),
                }
                for r in categoria_rows
            ],
            "dictionary_terms_used": len(terms),
        }

    async def price_items(
        self,
        *,
        q: str,
        categoria_id: int | None = None,
        licitacion_ids: list[int] | None = None,
        limit: int = 200,
    ) -> list[Row[Any]]:
        pattern = f"%{q.strip()}%"
        statement = (
            select(
                Licitacion.codigo.label("licitacion_codigo"),
                Organismo.nombre.label("organismo"),
                LicitacionItem.nombre,
                LicitacionItem.descripcion,
                LicitacionItem.precio_unitario,
                LicitacionItem.cantidad,
                LicitacionItem.unidad,
                Licitacion.fecha_publicacion.label("fecha"),
                Categoria.codigo.label("categoria_codigo"),
                Categoria.nombre.label("categoria_nombre"),
            )
            .select_from(LicitacionItem)
            .join(Licitacion, Licitacion.id == LicitacionItem.licitacion_id)
            .outerjoin(Organismo, Organismo.id == Licitacion.organismo_id)
            .outerjoin(Categoria, Categoria.id == LicitacionItem.categoria_id)
            .where(
                LicitacionItem.precio_unitario.isnot(None),
                or_(LicitacionItem.nombre.ilike(pattern), LicitacionItem.descripcion.ilike(pattern)),
            )
        )
        if categoria_id is not None:
            statement = statement.where(LicitacionItem.categoria_id == categoria_id)
        if licitacion_ids is not None:
            statement = statement.where(id_in(LicitacionItem.licitacion_id, licitacion_ids))
        statement = statement.order_by(Licitacion.fecha_publicacion.desc()).limit(limit)

        result = await self._session.execute(statement)
        return list(result.all())

    async def competition_summary(self, *, licitacion_ids: list[int] | None = None) -> dict[str, Any]:
        """Real competitive-intensity indicators, averaged over the awards that
        actually report `cantidad_ofertas`/`ratio_adjudicacion` (not every award
        does), from core.adjudicacion."""
        known = Adjudicacion.cantidad_ofertas.isnot(None)
        if licitacion_ids is not None:
            known = known & id_in(Adjudicacion.licitacion_id, licitacion_ids)

        averages = (
            await self._session.execute(
                select(
                    func.avg(Adjudicacion.cantidad_ofertas),
                    func.avg(1 - Adjudicacion.ratio_adjudicacion),
                ).where(known)
            )
        ).one()
        oferentes_promedio, margen_promedio = averages

        rango = case(
            (Adjudicacion.cantidad_ofertas == 1, "1 oferente"),
            (Adjudicacion.cantidad_ofertas.between(2, 3), "2-3 oferentes"),
            (Adjudicacion.cantidad_ofertas.between(4, 6), "4-6 oferentes"),
            else_="7+ oferentes",
        ).label("rango")
        bucket_rows = (
            await self._session.execute(
                select(rango, func.count()).where(known).group_by(rango)
            )
        ).all()
        total = sum(count for _, count in bucket_rows)

        return {
            "oferentes_promedio": float(oferentes_promedio) if oferentes_promedio is not None else None,
            "margen_descuento_promedio": (
                float(margen_promedio) * 100 if margen_promedio is not None else None
            ),
            "total_adjudicaciones_con_oferentes": total,
            "distribucion_oferentes": [
                {
                    "rango_oferentes": label,
                    "total_procesos": count,
                    "porcentaje": round(count / total * 100, 1) if total else 0.0,
                }
                for label, count in bucket_rows
            ],
        }

    async def data_quality_missing_keys(self) -> list[DQMissingKeys]:
        result = await self._session.execute(
            select(DQMissingKeys).order_by(DQMissingKeys.missing_count.desc())
        )
        return list(result.scalars().all())

    async def adjudicacion_snapshots(
        self,
        *,
        external_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        risk_level: str | None = None,
        only_outliers: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AdjudicacionAnalyticsSnapshot]:
        statement = select(AdjudicacionAnalyticsSnapshot)
        if external_id:
            statement = statement.where(AdjudicacionAnalyticsSnapshot.external_id == external_id)
        if start_date is not None:
            statement = statement.where(AdjudicacionAnalyticsSnapshot.snapshot_date >= start_date)
        if end_date is not None:
            statement = statement.where(AdjudicacionAnalyticsSnapshot.snapshot_date <= end_date)
        if risk_level:
            statement = statement.where(
                AdjudicacionAnalyticsSnapshot.risk_level == risk_level.strip().lower()
            )
        if only_outliers:
            statement = statement.where(AdjudicacionAnalyticsSnapshot.is_outlier.is_(True))
        result = await self._session.execute(
            statement.order_by(
                AdjudicacionAnalyticsSnapshot.snapshot_date.desc(),
                AdjudicacionAnalyticsSnapshot.scored_at.desc(),
                AdjudicacionAnalyticsSnapshot.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _rows(self, statement: Any, offset: int, limit: int) -> list[Row[Any]]:
        if offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        if not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        result = await self._session.execute(statement.offset(offset).limit(limit))
        return list(result.all())
