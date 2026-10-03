from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.dependencies import get_contrato_service
from app.schemas.common import CursorPage
from app.schemas.contrato import Contrato
from app.services.contrato import ContratoService
from app.api.v1.endpoints._pagination import make_page, parse_cursor

router = APIRouter()


@router.get(
    "/",
    response_model=CursorPage[Contrato],
    tags=["Contratos"],
    summary="List contratos",
    description="Keyset-paginated list of awarded contracts, ordered by id. Pass the previous "
    "response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
async def list_contratos(
    service: ContratoService = Depends(get_contrato_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
) -> CursorPage[Contrato]:
    parsed = parse_cursor(cursor, "contratos")
    page = await service.page(limit=limit, anchor_id=parsed.anchor_id if parsed else None, direction=parsed.direction if parsed else "next")
    return make_page(page, "contratos", limit)


@router.get(
    "/{contrato_id}",
    response_model=Contrato,
    tags=["Contratos"],
    summary="Get a contrato by id",
    responses={404: {"description": "Contrato not found."}},
)
async def get_contrato(
    contrato_id: int,
    service: ContratoService = Depends(get_contrato_service),
) -> Contrato:
    contrato = await service.get(contrato_id)
    if contrato is None:
        raise HTTPException(status_code=404, detail="Contrato not found")
    return contrato
