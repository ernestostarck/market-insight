from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.db.dependencies import get_adjudicacion_repository, get_segmento_licitacion_ids
from app.repositories.adjudicacion import AdjudicacionRepository
from app.schemas.adjudicacion import AdjudicacionListItem
from app.schemas.common import OffsetPage

router = APIRouter()


@router.get(
    "",
    response_model=OffsetPage[AdjudicacionListItem],
    summary="List adjudicaciones",
    description="Real awards from `core.adjudicacion`, server-sorted and offset-paginated, "
    "searchable (accent-insensitive) by tender code/name, supplier name/RUT and buyer name.",
)
async def list_adjudicaciones(
    repository: AdjudicacionRepository = Depends(get_adjudicacion_repository),
    limit: int = Query(10, ge=1, le=100, description="Page size."),
    offset: int = Query(0, ge=0, description="Index of the first record to return."),
    sort_by: Literal[
        "fecha_adjudicacion", "monto_adjudicado", "proveedor_razon_social", "organismo_nombre"
    ] = Query("fecha_adjudicacion"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    q: str | None = Query(None, max_length=200, description="Free-text search."),
    monto_min: float | None = Query(None, ge=0, description="Minimum awarded amount, in CLP."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> OffsetPage[AdjudicacionListItem]:
    items, total = await repository.get_ranking(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        monto_min=monto_min,
        licitacion_ids=licitacion_ids,
    )
    return OffsetPage(data=items, total=total, offset=offset, limit=limit)
