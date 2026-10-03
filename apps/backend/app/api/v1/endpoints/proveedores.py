from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.endpoints._pagination import make_page, parse_cursor
from app.db.dependencies import get_proveedor_service, get_segmento_licitacion_ids
from app.schemas.common import CursorPage, FacetCount, OffsetPage
from app.schemas.proveedor import Proveedor
from app.services.proveedor import ProveedorService

router = APIRouter()


@router.get(
    "",
    response_model=CursorPage[Proveedor],
    summary="List proveedores",
    description="Keyset-paginated list of suppliers, ordered by id, with performance stats "
    "(participation, awards, success rate, main category). Pass the previous response's "
    "`next_cursor`/`prev_cursor` in `cursor` to page forward/backward.",
)
@router.get(
    "/",
    response_model=CursorPage[Proveedor],
    include_in_schema=False,
)
async def list_proveedores(
    service: ProveedorService = Depends(get_proveedor_service),
    limit: int = Query(50, ge=1, le=100, description="Page size."),
    cursor: str | None = Query(None, description="Opaque cursor from a previous page."),
    q: str | None = Query(
        None, description="Case-insensitive search over rut, razon_social and nombre_fantasia."
    ),
    region: str | None = Query(None, description="Exact match on the supplier's region."),
    rubro: str | None = Query(
        None, description="Exact match on categoria_principal (the supplier's main award category)."
    ),
    tasa_minima: float | None = Query(
        None, ge=0, le=100, description="Minimum tasa_exito (award rate, percent)."
    ),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> CursorPage[Proveedor]:
    parsed = parse_cursor(cursor, "proveedores")
    page = await service.page(
        limit=limit,
        anchor_id=parsed.anchor_id if parsed else None,
        direction=parsed.direction if parsed else "next",
        q=q,
        region=region,
        rubro=rubro,
        tasa_minima=tasa_minima,
        licitacion_ids=licitacion_ids,
    )
    return make_page(page, "proveedores", limit)


@router.get(
    "/ranking",
    response_model=OffsetPage[Proveedor],
    summary="Ranking of proveedores",
    description="Server-sorted, offset-paginated suppliers with performance stats — e.g. "
    "`?limit=10&sort_by=monto_total_adjudicado` returns the top 10 by awarded amount.",
)
async def proveedores_ranking(
    service: ProveedorService = Depends(get_proveedor_service),
    limit: int = Query(10, ge=1, le=100, description="Page size (the N in \"top N\")."),
    offset: int = Query(0, ge=0, description="Index of the first record to return."),
    sort_by: Literal[
        "monto_total_adjudicado", "total_adjudicaciones", "tasa_exito", "razon_social"
    ] = Query("monto_total_adjudicado", description="Ranking criterion."),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    q: str | None = Query(None, description="Search over rut, razon_social and nombre_fantasia."),
    rubro: str | None = Query(None, description="Exact match on categoria_principal."),
    tasa_minima: float | None = Query(None, ge=0, le=100, description="Minimum tasa_exito, percent."),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> OffsetPage[Proveedor]:
    items, total = await service.ranking(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        rubro=rubro,
        tasa_minima=tasa_minima,
        licitacion_ids=licitacion_ids,
    )
    return OffsetPage(data=items, total=total, offset=offset, limit=limit)


@router.get(
    "/rubros",
    response_model=list[FacetCount],
    summary="Main award categories among proveedores",
    description="Most common `categoria_principal` values with their supplier counts, to "
    "populate the rubro filter with real options.",
)
async def proveedores_rubros(
    service: ProveedorService = Depends(get_proveedor_service),
    licitacion_ids: list[int] | None = Depends(get_segmento_licitacion_ids),
) -> list[FacetCount]:
    facets = await service.categoria_facets(licitacion_ids=licitacion_ids)
    return [FacetCount(value=value, count=count) for value, count in facets]


@router.get(
    "/{proveedor_id}",
    response_model=Proveedor,
    summary="Get a proveedor by id",
    responses={404: {"description": "Proveedor not found."}},
)
async def get_proveedor(
    proveedor_id: int,
    service: ProveedorService = Depends(get_proveedor_service),
) -> Proveedor:
    proveedor = await service.get(proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor not found")
    return proveedor
