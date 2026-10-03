"""Shared free-text matching for list filters."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def matches_text(query: str, *columns: ColumnElement[str]) -> ColumnElement[bool]:
    """Case- and accent-insensitive substring match of `query` against any column.

    Uses Postgres `unaccent` (installed by docker/postgres/init/001-extensions.sql),
    so "construccion" finds "Construcción" and "rio bueno" finds "RÍO BUENO".
    """
    pattern = func.unaccent(f"%{_escape_like(query.strip())}%")
    return or_(*(func.unaccent(column).ilike(pattern, escape="\\") for column in columns))
