"""Contracts for the cross-entity search use case."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SearchEntity = Literal["licitacion", "proveedor", "organismo"]


class SearchQuery(BaseModel):
    """Validated input for a cross-entity text search."""

    query: str = Field(min_length=2, max_length=200, description="Text to search for.")
    entities: set[SearchEntity] = Field(
        default_factory=lambda: {"licitacion", "proveedor", "organismo"},
        description="Entity types included in the search.",
    )
    limit_per_entity: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("query must contain at least two non-whitespace characters")
        return normalized

    @model_validator(mode="after")
    def require_entity(self) -> "SearchQuery":
        if not self.entities:
            raise ValueError("at least one entity must be selected")
        return self


class SearchResult(BaseModel):
    entity_type: SearchEntity = Field(..., description="Which entity type this result came from.")
    id: int = Field(..., description="Id of the matched record within its own entity type.")
    title: str = Field(..., description="Primary display label for the match.")
    subtitle: str | None = Field(None, description="Secondary display label, if any.")
    code: str | None = Field(None, description="Domain code (e.g. tender code, RUT), if any.")
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, description="Extra entity-specific fields."
    )


class SearchResponse(BaseModel):
    query: str = Field(..., description="Normalized query text that was searched.")
    entities: list[SearchEntity] = Field(..., description="Entity types that were searched.")
    total: int = Field(..., description="Total number of results across all entities.")
    results: list[SearchResult]
