from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.endpoints._pagination import make_page, parse_cursor
from app.db.dependencies import get_categoria_service, get_segmento_licitacion_ids
from app.schemas.categoria import Categoria, CategoriaDetail
from app.schemas.common import CursorPage, OffsetPage
from app.services.categoria import CategoriaService

router = APIRouter()


@router.get(
    "",
    response_model=CursorPage[Categoria],
    summary="List rubros (core.categoria)",
    description="Keyset-paginated list of ChileCompra rubros, ordered by id, with real award "
    "stats (tenders, amount, suppliers, buyers) computed from core.licitacion/core.adjudicacion. "
    "Pass the previous response's `next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
@router.get(
    "/",
    response_model=CursorPage[Categoria],
    include_in_schema=False,
)
async def list_categorias(
    service: CategoriaService = Depends(get_categoria_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
    q: str | None = Query(None, description="Case-insensitive search over codigo and nombre."),
    monto_minimo: float | None = Query(None, ge=0, description="Minimum monto_total awarded, in CLP."),
) -> CursorPage[Categoria]:
    parsed = parse_cursor(cursor, "categorias")
    page = await service.page(
        limit=limit,
        anchor_id=parsed.anchor_id if parsed else None,
        direction=parsed.direction if parsed else "next",
        q=q,
        monto_minimo=monto_minimo,
    )
    return make_page(page, "categorias", limit)


@router.get(
    "/ranking",
    response_model=OffsetPage[Categoria],
    summary="Ranking of rubros",
    description="Server-sorted, offset-paginated rubros with award stats — e.g. "
    "`?limit=10&sort_by=monto_total` returns the top 10 by awarded amount. `q` is "
    "case- and accent-insensitive.",
)
async def categorias_ranking(
    service: CategoriaService = Depends(get_categoria_service),
    limit: int = Query(10, ge=1, le=100, description="Page size (the N in \"top N\")."),
    offset: int = Query(0, ge=0, description="Index of the first record to return."),
    sort_by: Literal["monto_total", "total_licitaciones", "total_proveedores", "codigo", "nombre"] = Query(
        "monto_total", description="Ranking criterion."
    ),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    q: str | None = Query(None, max_length=200, description="Search over codigo and nombre."),
    monto_minimo: float | None = Query(None, ge=0, description="Minimum monto_total awarded, in CLP."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> OffsetPage[Categoria]:
    items, total = await service.ranking(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        monto_minimo=monto_minimo,
        licitacion_ids=licitacion_ids,
    )
    return OffsetPage(data=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{categoria_id}",
    response_model=CategoriaDetail,
    summary="Get a categoria by id, with its top suppliers and buyers",
    responses={404: {"description": "Categoria not found."}},
)
async def get_categoria(
    categoria_id: int,
    service: CategoriaService = Depends(get_categoria_service),
) -> CategoriaDetail:
    categoria = await service.get(categoria_id)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoria not found")
    return categoria
