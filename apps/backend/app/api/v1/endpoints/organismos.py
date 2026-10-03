from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dependencies import get_organismo_service, get_segmento_licitacion_ids
from app.schemas.common import CursorPage, OffsetPage
from app.schemas.organismo import Organismo, OrganismoRanking
from app.services.organismo import OrganismoService
from app.api.v1.endpoints._pagination import make_page, parse_cursor

router = APIRouter()


@router.get(
    "",
    response_model=CursorPage[Organismo],
    summary="List organismos",
    description="Keyset-paginated list of buying agencies, ordered by id. Pass the previous "
    "response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
@router.get(
    "/",
    response_model=CursorPage[Organismo],
    include_in_schema=False,
)
async def list_organismos(
    service: OrganismoService = Depends(get_organismo_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> CursorPage[Organismo]:
    parsed = parse_cursor(cursor, "organismos")
    page = await service.page(
        limit=limit,
        anchor_id=parsed.anchor_id if parsed else None,
        direction=parsed.direction if parsed else "next",
        licitacion_ids=licitacion_ids,
    )
    return make_page(page, "organismos", limit)


@router.get(
    "/ranking",
    response_model=OffsetPage[OrganismoRanking],
    summary="Ranking of organismos",
    description="Server-sorted, offset-paginated buying agencies with purchasing stats — e.g. "
    "`?limit=10&sort_by=monto_total_comprado` returns the top 10 buyers by awarded amount.",
)
async def organismos_ranking(
    service: OrganismoService = Depends(get_organismo_service),
    limit: int = Query(10, ge=1, le=100, description="Page size (the N in \"top N\")."),
    offset: int = Query(0, ge=0, description="Index of the first record to return."),
    sort_by: Literal[
        "monto_total_comprado", "total_licitaciones", "licitaciones_activas", "nombre"
    ] = Query("monto_total_comprado", description="Ranking criterion."),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    q: str | None = Query(None, description="Search over nombre and codigo."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> OffsetPage[OrganismoRanking]:
    items, total = await service.ranking(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        licitacion_ids=licitacion_ids,
    )
    return OffsetPage(data=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{organismo_id}",
    response_model=Organismo,
    summary="Get an organismo by id",
    responses={404: {"description": "Organismo not found."}},
)
async def get_organismo(
    organismo_id: int,
    service: OrganismoService = Depends(get_organismo_service),
) -> Organismo:
    organismo = await service.get(organismo_id)
    if organismo is None:
        raise HTTPException(status_code=404, detail="Organismo not found")
    return organismo
