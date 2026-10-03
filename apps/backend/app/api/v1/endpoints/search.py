"""HTTP interface for federated canonical-entity search."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.dependencies import get_search_service
from app.schemas.search import SearchEntity, SearchQuery, SearchResponse
from app.services.search import SearchService

router = APIRouter()


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search procurement entities",
    description=(
        "Searches licitaciones, proveedores and organismos concurrently. "
        "Repeated `entity` query parameters restrict the sources to search."
    ),
)
async def search(
    q: Annotated[
        str,
        Query(
            min_length=2,
            max_length=200,
            description="Text to find in canonical procurement entities.",
        ),
    ],
    entity: Annotated[
        list[SearchEntity] | None,
        Query(description="Optional source entity; may be repeated."),
    ] = None,
    limit_per_entity: Annotated[
        int,
        Query(ge=1, le=50, description="Maximum matches returned for each entity."),
    ] = 10,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    """Run a validated federated text search."""
    return await service.search(
        SearchQuery(
            query=q,
            entities=set(entity) if entity else {"licitacion", "proveedor", "organismo"},
            limit_per_entity=limit_per_entity,
        )
    )
