from typing import Any

from sqlalchemy import Row, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.categoria import Categoria
from app.models.core.licitacion import Licitacion
from app.models.core.organismo import Organismo
from app.nlp.segmento import id_in
from app.repositories.pagination import KeysetPage
from app.repositories.text_search import matches_text
from app.schemas.categoria import split_rubro_breadcrumb
from app.schemas.licitacion import Licitacion as LicitacionSchema
from app.schemas.licitacion import LicitacionCreate
from app.schemas.organismo import Organismo as OrganismoSchema


class LicitacionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _statement(self):
        return (
            select(Licitacion, Organismo, Categoria)
            .select_from(Licitacion)
            .outerjoin(Organismo, Organismo.id == Licitacion.organismo_id)
            .outerjoin(Categoria, Categoria.id == Licitacion.categoria_id)
        )

    @staticmethod
    def _row_to_schema(row: Row[Any]) -> LicitacionSchema:
        licitacion: Licitacion = row.Licitacion
        organismo: Organismo | None = row.Organismo
        categoria: Categoria | None = row.Categoria
        _, _, clase = split_rubro_breadcrumb(categoria.nombre if categoria else None)
        return LicitacionSchema(
            id=licitacion.id,
            codigo=licitacion.codigo,
            nombre=licitacion.nombre,
            descripcion=licitacion.descripcion,
            estado=_estado_label(licitacion.estado),
            fecha_publicacion=licitacion.fecha_publicacion,
            fecha_cierre=licitacion.fecha_cierre,
            monto_estimado=(
                float(licitacion.monto_estimado) if licitacion.monto_estimado is not None else None
            ),
            organismo_id=licitacion.organismo_id,
            organismo=OrganismoSchema.model_validate(organismo) if organismo else None,
            categoria=clase or (categoria.nombre if categoria else None),
        )

    async def get_multi(self, skip: int = 0, limit: int = 100) -> list[Licitacion]:
        result = await self.session.execute(
            select(Licitacion).order_by(Licitacion.id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def search_by_text(self, query: str, limit: int = 100) -> list[Licitacion]:
        pattern = f"%{_escape_like(query)}%"
        result = await self.session.execute(
            select(Licitacion)
            .where(
                or_(
                    Licitacion.codigo.ilike(pattern, escape="\\"),
                    Licitacion.nombre.ilike(pattern, escape="\\"),
                    Licitacion.descripcion.ilike(pattern, escape="\\"),
                )
            )
            .order_by(Licitacion.fecha_publicacion.desc(), Licitacion.id.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get(self, licitacion_id: int) -> LicitacionSchema | None:
        result = await self.session.execute(
            self._statement().where(Licitacion.id == licitacion_id)
        )
        row = result.first()
        return self._row_to_schema(row) if row else None

    async def get_page_filtered(
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
    ) -> KeysetPage[LicitacionSchema]:
        statement = self._statement()
        if licitacion_ids is not None:
            statement = statement.where(id_in(Licitacion.id, licitacion_ids))

        if q:
            statement = statement.where(
                matches_text(
                    q, Licitacion.codigo, Licitacion.nombre, Licitacion.descripcion, Organismo.nombre
                )
            )
        if estado:
            statement = statement.where(Licitacion.estado.in_(_estado_values(estado)))
        if organismo_id is not None:
            statement = statement.where(Licitacion.organismo_id == organismo_id)
        if monto_min is not None:
            statement = statement.where(Licitacion.monto_estimado >= monto_min)
        if monto_max is not None:
            statement = statement.where(Licitacion.monto_estimado <= monto_max)

        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))

        if anchor_id is not None:
            operator = Licitacion.id > anchor_id if direction == "next" else Licitacion.id < anchor_id
            statement = statement.where(operator)
        order = Licitacion.id.asc() if direction == "next" else Licitacion.id.desc()
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

    async def create(self, payload: LicitacionCreate) -> Licitacion:
        db_obj = Licitacion(**payload.model_dump())
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj


# ChileCompra CodigoEstado -> label. core.licitacion stores the raw code.
_ESTADO_LABELS = {"5": "publicada", "6": "cerrada", "7": "desierta", "8": "adjudicada", "18": "revocada", "19": "suspendida"}
_ESTADO_CODES = {label: code for code, label in _ESTADO_LABELS.items()}


def _estado_label(estado: str | None) -> str | None:
    return _ESTADO_LABELS.get(estado, estado) if estado else estado


def _estado_values(estado: str) -> list[str]:
    """Accept either the label (publicada) or the raw code (5) as a filter value."""
    value = estado.strip().lower()
    code = _ESTADO_CODES.get(value)
    return [value, code] if code else [value, _ESTADO_LABELS.get(value, value)]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
