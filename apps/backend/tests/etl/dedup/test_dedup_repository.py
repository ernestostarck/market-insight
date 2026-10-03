from __future__ import annotations

from app.etl.dedup.repository import (
    ExistingRecord,
    InMemoryDedupRepository,
    SqlAlchemyDedupRepository,
)


class _FakeRow:
    def __init__(self, natural_key: str, payload_hash: str | None) -> None:
        self._key = natural_key
        self._hash = payload_hash

    def __getitem__(self, index: int) -> object:
        if index == 0:
            return self._key
        return self._hash


class _FakeResult:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_FakeRow]:
        return self._rows


class _FakeConnection:
    def __init__(self, rows_by_sql: dict[str, list[_FakeRow]]) -> None:
        self._rows_by_sql = rows_by_sql
        self.executed: list[str] = []

    def execute(self, statement, params=None):
        self.executed.append(str(statement))
        sql_text = str(statement)
        return _FakeResult(self._rows_by_sql.get(sql_text, []))


def test_sql_repository_builds_bounded_in_query() -> None:
    rows = [
        _FakeRow("licitacion:chilecompra:1000-1-LP26", "hash-a"),
        _FakeRow("licitacion:chilecompra:1000-2-LP26", "hash-b"),
    ]
    conn = _FakeConnection(
        {
            "SELECT natural_key, payload_hash FROM procurement.licitaciones WHERE natural_key IN (:k0, :k1)": rows,
        }
    )
    repo = SqlAlchemyDedupRepository(conn)

    existing = repo.get_existing_batch(
        "licitacion",
        ["licitacion:chilecompra:1000-1-LP26", "licitacion:chilecompra:1000-2-LP26"],
    )

    assert len(existing) == 2
    assert existing["licitacion:chilecompra:1000-1-LP26"].payload_hash == "hash-a"
    assert existing["licitacion:chilecompra:1000-2-LP26"].payload_hash == "hash-b"
    assert "procurement.licitaciones" in conn.executed[0]


def test_sql_repository_returns_empty_for_unknown_table() -> None:
    conn = _FakeConnection({})
    repo = SqlAlchemyDedupRepository(conn)

    existing = repo.get_existing_batch("unknown_entity", ["k1"])

    assert existing == {}


def test_sql_repository_returns_empty_for_no_keys() -> None:
    conn = _FakeConnection({})
    repo = SqlAlchemyDedupRepository(conn)

    existing = repo.get_existing_batch("licitacion", [])

    assert existing == {}


def test_in_memory_repository_seeded_lookup() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-1-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-1-LP26",
                payload_hash="hash-a",
            )
        }
    )

    existing = repo.get_existing_batch(
        "licitacion",
        ["licitacion:chilecompra:1000-1-LP26", "licitacion:chilecompra:1000-3-LP26"],
    )

    assert len(existing) == 1
    assert existing["licitacion:chilecompra:1000-1-LP26"].payload_hash == "hash-a"


def test_in_memory_repository_per_entity_buckets() -> None:
    repo = InMemoryDedupRepository(
        {
            "licitacion:chilecompra:1000-1-LP26": ExistingRecord(
                natural_key="licitacion:chilecompra:1000-1-LP26",
                payload_hash="hash-l",
            ),
            "empresa:chilecompra:EMPRESA-1": ExistingRecord(
                natural_key="empresa:chilecompra:EMPRESA-1",
                payload_hash="hash-e",
            ),
        }
    )

    licitaciones = repo.get_existing_batch(
        "licitacion", ["licitacion:chilecompra:1000-1-LP26"]
    )
    empresas = repo.get_existing_batch("empresa", ["empresa:chilecompra:EMPRESA-1"])

    assert len(licitaciones) == 1
    assert len(empresas) == 1
