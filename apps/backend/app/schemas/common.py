from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataType = TypeVar("DataType")


class FacetCount(BaseModel):
    value: str = Field(..., description="Distinct value of the faceted field.")
    count: int = Field(..., ge=0, description="Number of records with this value.")


class OffsetPage(BaseModel, Generic[DataType]):
    """Offset-paginated, server-sorted page (rankings: "top N by monto", etc.)."""

    data: list[DataType] = Field(default_factory=list)
    total: int = Field(default=0, ge=0, description="Total records matching the filters.")
    offset: int = Field(default=0, ge=0, description="Index of the first returned record.")
    limit: int = Field(default=10, ge=1, description="Maximum records requested for this page.")


class CursorPage(BaseModel, Generic[DataType]):
    data: list[DataType] = Field(default_factory=list)
    total: int = Field(default=0, ge=0, description="Total records matching the current resource.")
    page_size: int = Field(default=50, ge=1, description="Maximum records requested for this page.")
    next_cursor: str | None = Field(
        None, description="The cursor to use to fetch the next page of results."
    )
    previous_cursor: str | None = Field(
        None, description="The cursor to use to fetch the previous page of results."
    )
    has_next: bool = False
    has_previous: bool = False
