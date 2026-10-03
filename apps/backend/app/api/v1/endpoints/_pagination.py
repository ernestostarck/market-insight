from __future__ import annotations

from fastapi import HTTPException

from app.core.pagination import Cursor, encode_cursor
from app.repositories.pagination import KeysetPage
from app.schemas.common import CursorPage


def parse_cursor(token: str | None, resource: str) -> Cursor | None:
    if token is None:
        return None
    from app.core.pagination import decode_cursor

    try:
        return decode_cursor(token, resource)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def make_page(page: KeysetPage, resource: str, limit: int) -> CursorPage:
    first_id = page.items[0].id if page.items else None
    last_id = page.items[-1].id if page.items else None
    return CursorPage(
        data=page.items,
        total=page.total,
        page_size=limit,
        next_cursor=(encode_cursor(resource, last_id, "next") if page.has_next and last_id else None),
        previous_cursor=(encode_cursor(resource, first_id, "previous") if page.has_previous and first_id else None),
        has_next=page.has_next,
        has_previous=page.has_previous,
    )
