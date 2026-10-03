from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dependencies import get_licitacion_service, get_segmento_licitacion_ids
from app.schemas.common import CursorPage
from app.schemas.licitacion import Licitacion
from app.services.licitacion import LicitacionService
from app.api.v1.endpoints._pagination import make_page, parse_cursor

router = APIRouter()


@router.get(
    "",
    response_model=CursorPage[Licitacion],
    tags=["Licitaciones"],
    summary="List licitaciones",
    description="Keyset-paginated list of tenders, ordered by id. Pass the previous "
    "response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
@router.get(
    "/",
    response_model=CursorPage[Licitacion],
    include_in_schema=False,
)
async def list_licitaciones(
    service: LicitacionService = Depends(get_licitacion_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
    q: str | None = Query(None, description="Case-insensitive search over codigo, nombre, descripcion and organismo."),
    estado: str | None = Query(None, description="Filter by tender status."),
    organismo_id: int | None = Query(None, description="Filter by buying agency id."),
    monto_min: float | None = Query(None, ge=0, description="Minimum monto_estimado, in CLP."),
    monto_max: float | None = Query(None, ge=0, description="Maximum monto_estimado, in CLP."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> CursorPage[Licitacion]:
    parsed = parse_cursor(cursor, "licitaciones")
    page = await service.page(
        limit=limit,
        anchor_id=parsed.anchor_id if parsed else None,
        direction=parsed.direction if parsed else "next",
        q=q,
        estado=estado,
        organismo_id=organismo_id,
        monto_min=monto_min,
        monto_max=monto_max,
        licitacion_ids=licitacion_ids,
    )
    return make_page(page, "licitaciones", limit)


@router.get(
    "/{licitacion_id}",
    response_model=Licitacion,
    tags=["Licitaciones"],
    summary="Get a licitacion by id",
    responses={404: {"description": "Licitacion not found."}},
)
async def get_licitacion(
    licitacion_id: int,
    service: LicitacionService = Depends(get_licitacion_service),
) -> Licitacion:
    licitacion = await service.get(licitacion_id)
    if licitacion is None:
        raise HTTPException(status_code=404, detail="Licitacion not found")
    return licitacion
