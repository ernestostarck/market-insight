from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeEngine


def jsonb_type() -> TypeEngine:
    """Return a JSON type that uses JSONB on PostgreSQL and JSON elsewhere."""
    return JSON().with_variant(JSONB, "postgresql")
