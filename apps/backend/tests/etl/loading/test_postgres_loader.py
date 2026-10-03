from __future__ import annotations

from datetime import datetime

from app.etl.loading.postgres import PostgresRecordLoader
from app.etl.models import (
    IngestionRunContext,
    LoadResult,
    TransformedRecord,
)


class FakeRow:
    def __init__(self, value):
        self._value = value

    def __getitem__(self, index):
        return self._value


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    """In-memory connection capturing executed upsert statements."""

    def __init__(self) -> None:
        self.stored: dict[str, str] = {}  # natural_key -> payload_hash
        self.upserts: list[str] = []
        self.closed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if sql.strip().upper().startswith("SELECT"):
            # Shape: SELECT payload_hash FROM ... WHERE natural_key = :natural_key
            natural_key = params["natural_key"]
            return FakeResult(
                [FakeRow(self.stored.get(natural_key))]
                if natural_key in self.stored
                else []
            )
        # INSERT ... upsert
        self.upserts.append(sql)
        natural_key = params["natural_key"]
        payload_hash = params["payload_hash"]
        self.stored[natural_key] = payload_hash
        return FakeResult([])

    def close(self) -> None:
        self.closed = True


def _run() -> IngestionRunContext:
    return IngestionRunContext(
        ingestion_run_id="run-load-1",
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="0.1.0",
        started_at=datetime(2026, 8, 7, 12, 0, 0),
    )


def _record(entity, key, payload_hash, **payload) -> TransformedRecord:
    data = {"external_id": key, **payload}
    return TransformedRecord(
        entity=entity,
        natural_key=f"chilecompra:{entity}:{key}",
        payload=data,
        source_id=key,
        payload_hash=payload_hash,
    )


def test_load_inserts_new_records() -> None:
    connection = FakeConnection()
    loader = PostgresRecordLoader(lambda: connection)

    records = [
        _record("licitacion", "1000-1-LR26", "hash-a", title="Compra A"),
        _record("licitacion", "1000-2-LR26", "hash-b", title="Compra B"),
    ]

    result = loader.load(_run(), records)

    assert isinstance(result, LoadResult)
    assert result.inserted == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert len(connection.upserts) == 2
    assert connection.closed is True


def test_load_counts_unchanged_and_updates() -> None:
    connection = FakeConnection()
    connection.stored["chilecompra:licitacion:1000-1-LR26"] = "hash-same"
    connection.stored["chilecompra:licitacion:1000-2-LR26"] = "hash-old"
    loader = PostgresRecordLoader(lambda: connection)

    records = [
        _record("licitacion", "1000-1-LR26", "hash-same", title="Sin cambios"),
        _record("licitacion", "1000-2-LR26", "hash-new", title="Cambio"),
    ]

    result = loader.load(_run(), records)

    assert result.inserted == 0
    assert result.updated == 1
    assert result.unchanged == 1
    assert len(connection.upserts) == 1


def test_load_empty_records_returns_zero_without_connection() -> None:
    def factory() -> FakeConnection:
        raise AssertionError("No connection should be opened for empty input")

    loader = PostgresRecordLoader(factory)

    result = loader.load(_run(), [])

    assert result.inserted == 0
    assert result.updated == 0
    assert result.unchanged == 0


def test_load_upsert_uses_proper_columns() -> None:
    connection = FakeConnection()
    loader = PostgresRecordLoader(lambda: connection)

    record = _record(
        "licitacion",
        "1000-1-LR26",
        "hash-a",
        title="Compra",
        status="ADJUDICADA",
    )
    loader.load(_run(), [record])

    sql = connection.upserts[0]
    assert "procurement.licitaciones" in sql
    assert "ON CONFLICT" in sql
    assert "title" in sql
    assert "status" in sql
