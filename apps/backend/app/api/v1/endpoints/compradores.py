from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dependencies import get_comprador_service
from app.schemas.common import CursorPage
from app.schemas.comprador import Comprador
from app.services.comprador import CompradorService
from app.api.v1.endpoints._pagination import make_page, parse_cursor

router = APIRouter()


@router.get(
    "/",
    response_model=CursorPage[Comprador],
    tags=["Compradores"],
    summary="List compradores",
    description="Keyset-paginated list of buyers, ordered by id. Pass the previous "
    "response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
async def list_compradores(
    service: CompradorService = Depends(get_comprador_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
) -> CursorPage[Comprador]:
    parsed = parse_cursor(cursor, "compradores")
    page = await service.page(limit=limit, anchor_id=parsed.anchor_id if parsed else None, direction=parsed.direction if parsed else "next")
    return make_page(page, "compradores", limit)


@router.get(
    "/{comprador_id}",
    response_model=Comprador,
    tags=["Compradores"],
    summary="Get a comprador by id",
    responses={404: {"description": "Comprador not found."}},
)
async def get_comprador(
    comprador_id: int,
    service: CompradorService = Depends(get_comprador_service),
) -> Comprador:
    comprador = await service.get(comprador_id)
    if comprador is None:
        raise HTTPException(status_code=404, detail="Comprador not found")
    return comprador
