"""Reusable database operations for ID-based keyset pagination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")
Direction = Literal["next", "previous"]


@dataclass(slots=True)
class KeysetPage(Generic[ModelT]):
    items: list[ModelT]
    total: int
    has_next: bool
    has_previous: bool


async def fetch_keyset_page(
    session: AsyncSession,
    model: type[ModelT],
    *,
    limit: int,
    anchor_id: int | None = None,
    direction: Direction = "next",
    where: ColumnElement[bool] | None = None,
) -> KeysetPage[ModelT]:
    """Fetch a stable page ordered by the model's integer ``id`` column, optionally filtered."""
    statement = select(model)
    if where is not None:
        statement = statement.where(where)
    if anchor_id is not None:
        operator = model.id > anchor_id if direction == "next" else model.id < anchor_id
        statement = statement.where(operator)
    order = model.id.asc() if direction == "next" else model.id.desc()
    result = await session.execute(statement.order_by(order).limit(limit + 1))
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    items = rows[:limit]
    if direction == "previous":
        items.reverse()

    count_statement = select(func.count()).select_from(model)
    if where is not None:
        count_statement = count_statement.where(where)
    total = await session.scalar(count_statement)
    if direction == "next":
        has_previous = anchor_id is not None and bool(items)
        has_next = has_more
    else:
        has_previous = has_more
        has_next = bool(items)
    return KeysetPage(
        items=items,
        total=total or 0,
        has_next=has_next,
        has_previous=has_previous,
    )
