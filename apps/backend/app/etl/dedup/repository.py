from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.etl.loading.mapping import has_table, table_for


@dataclass(frozen=True, slots=True)
class ExistingRecord:
    natural_key: str
    payload_hash: str | None


class DedupRepository(Protocol):
    """Contract for lookup of already-persisted analytical records."""

    def get_existing_batch(
        self,
        entity: str,
        natural_keys: Iterable[str],
    ) -> dict[str, ExistingRecord]: ...


class SqlAlchemyDedupRepository:
    """Dedup lookup backed by the procurement.* analytical tables."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_existing_batch(
        self,
        entity: str,
        natural_keys: Iterable[str],
    ) -> dict[str, ExistingRecord]:
        if not has_table(entity):
            return {}
        keys = list(dict.fromkeys(natural_keys))
        if not keys:
            return {}

        mapping = table_for(entity)
        qualified = f"{mapping.schema}.{mapping.table}"
        placeholders = ", ".join(f":k{i}" for i in range(len(keys)))
        stmt = text(
            f"SELECT {mapping.natural_key_column}, {mapping.payload_hash_column} "
            f"FROM {qualified} WHERE {mapping.natural_key_column} IN ({placeholders})"
        )
        params = {f"k{i}": key for i, key in enumerate(keys)}
        rows = self._connection.execute(stmt, params).fetchall()

        return {
            str(row[0]): ExistingRecord(
                natural_key=str(row[0]),
                payload_hash=str(row[1]) if row[1] is not None else None,
            )
            for row in rows
        }


class InMemoryDedupRepository:
    """In-memory dedup repository used for tests and validation.

    Seeds are keyed by full ``natural_key`` (``<entity>:<source>:<id>``).
    ``get_existing_batch`` filters by the entity prefix so lookups behave like
    the SQL repository, which queries one analytical table per entity.
    """

    def __init__(self, seed: dict[str, ExistingRecord] | None = None) -> None:
        self._existing: dict[str, ExistingRecord] = dict(seed or {})

    def get_existing_batch(
        self,
        entity: str,
        natural_keys: Iterable[str],
    ) -> dict[str, ExistingRecord]:
        prefix = f"{entity}:"
        target_keys = set(natural_keys)
        return {
            key: record
            for key, record in self._existing.items()
            if key.startswith(prefix) and key in target_keys
        }
