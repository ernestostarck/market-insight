from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.licitacion import Adjudicacion, Licitacion
from app.models.core.organismo import Organismo
from app.models.core.proveedor import Proveedor
from app.nlp.segmento import id_in
from app.repositories.text_search import matches_text
from app.schemas.adjudicacion import AdjudicacionListItem


class AdjudicacionRepository:
    """Read access to real awards (`core.adjudicacion`) with their tender, supplier and buyer."""

    _SORTABLE = ("fecha_adjudicacion", "monto_adjudicado", "proveedor_razon_social", "organismo_nombre")

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ranking(
        self,
        *,
        limit: int,
        offset: int = 0,
        sort_by: str = "fecha_adjudicacion",
        sort_dir: str = "desc",
        q: str | None = None,
        monto_min: float | None = None,
        licitacion_ids: list[int] | None = None,
    ) -> tuple[list[AdjudicacionListItem], int]:
        if sort_by not in self._SORTABLE:
            raise ValueError(f"sort_by must be one of {self._SORTABLE}")

        organismo_id = func.coalesce(Adjudicacion.organismo_id, Licitacion.organismo_id)
        statement = (
            select(
                Adjudicacion.id,
                Adjudicacion.licitacion_id,
                Licitacion.codigo.label("licitacion_codigo"),
                Licitacion.nombre.label("licitacion_nombre"),
                Adjudicacion.proveedor_id,
                Proveedor.rut.label("proveedor_rut"),
                Proveedor.razon_social.label("proveedor_razon_social"),
                organismo_id.label("organismo_id"),
                Organismo.nombre.label("organismo_nombre"),
                Adjudicacion.monto_adjudicado,
                Adjudicacion.fecha_adjudicacion,
                Adjudicacion.ratio_adjudicacion,
            )
            .select_from(Adjudicacion)
            .join(Licitacion, Licitacion.id == Adjudicacion.licitacion_id)
            .outerjoin(Proveedor, Proveedor.id == Adjudicacion.proveedor_id)
            .outerjoin(Organismo, Organismo.id == organismo_id)
        )
        if licitacion_ids is not None:
            statement = statement.where(id_in(Adjudicacion.licitacion_id, licitacion_ids))
        if q:
            statement = statement.where(
                matches_text(
                    q,
                    Licitacion.codigo,
                    Licitacion.nombre,
                    Proveedor.razon_social,
                    Proveedor.rut,
                    Organismo.nombre,
                )
            )
        if monto_min is not None:
            statement = statement.where(Adjudicacion.monto_adjudicado >= monto_min)

        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))
        column = {
            "fecha_adjudicacion": Adjudicacion.fecha_adjudicacion,
            "monto_adjudicado": Adjudicacion.monto_adjudicado,
            "proveedor_razon_social": Proveedor.razon_social,
            "organismo_nombre": Organismo.nombre,
        }[sort_by]
        order = column.asc().nulls_last() if sort_dir == "asc" else column.desc().nulls_last()
        rows = (
            await self.session.execute(
                statement.order_by(order, Adjudicacion.id.desc()).offset(offset).limit(limit)
            )
        ).all()
        items = [
            AdjudicacionListItem(
                id=row.id,
                licitacion_id=row.licitacion_id,
                licitacion_codigo=row.licitacion_codigo,
                licitacion_nombre=row.licitacion_nombre,
                proveedor_id=row.proveedor_id,
                proveedor_rut=row.proveedor_rut,
                proveedor_razon_social=row.proveedor_razon_social,
                organismo_id=row.organismo_id,
                organismo_nombre=row.organismo_nombre,
                monto_adjudicado=float(row.monto_adjudicado) if row.monto_adjudicado is not None else None,
                fecha_adjudicacion=row.fecha_adjudicacion,
                # (awarded / estimated - 1) * 100: negative = closed below the reference price.
                desviacion_precio_referencial=(
                    round((float(row.ratio_adjudicacion) - 1) * 100, 1)
                    if row.ratio_adjudicacion is not None
                    else None
                ),
            )
            for row in rows
        ]
        return items, total or 0
