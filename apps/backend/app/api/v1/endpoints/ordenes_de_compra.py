from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dependencies import get_orden_de_compra_service
from app.schemas.common import CursorPage
from app.schemas.orden_de_compra import OrdenDeCompra
from app.services.orden_de_compra import OrdenDeCompraService
from app.api.v1.endpoints._pagination import make_page, parse_cursor

router = APIRouter()


@router.get(
    "",
    response_model=CursorPage[OrdenDeCompra],
    tags=["Ordenes de Compra"],
    summary="List ordenes de compra",
    description="Keyset-paginated list of purchase orders, ordered by id. Pass the previous "
    "response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
@router.get(
    "/",
    response_model=CursorPage[OrdenDeCompra],
    include_in_schema=False,
)
async def list_ordenes_de_compra(
    service: OrdenDeCompraService = Depends(get_orden_de_compra_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
) -> CursorPage[OrdenDeCompra]:
    parsed = parse_cursor(cursor, "ordenes_de_compra")
    page = await service.page(limit=limit, anchor_id=parsed.anchor_id if parsed else None, direction=parsed.direction if parsed else "next")
    return make_page(page, "ordenes_de_compra", limit)


@router.get(
    "/{orden_de_compra_id}",
    response_model=OrdenDeCompra,
    tags=["Ordenes de Compra"],
    summary="Get an orden de compra by id",
    responses={404: {"description": "Orden de Compra not found."}},
)
async def get_orden_de_compra(
    orden_de_compra_id: int,
    service: OrdenDeCompraService = Depends(get_orden_de_compra_service),
) -> OrdenDeCompra:
    orden_de_compra = await service.get(orden_de_compra_id)
    if orden_de_compra is None:
        raise HTTPException(status_code=404, detail="Orden de Compra not found")
    return orden_de_compra
