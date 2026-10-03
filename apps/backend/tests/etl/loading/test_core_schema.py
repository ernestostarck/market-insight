from __future__ import annotations

from datetime import datetime

from app.etl.loading.core_schema import CoreLicitacionItemLoader, CoreLicitacionLoader
from app.etl.models import IngestionRunContext, LoadResult, TransformedRecord
from app.integrations.chilecompra.models import LicitacionDetalleItem


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
    """In-memory stand-in for core.licitacion / core.organismo, same style as
    tests/etl/loading/test_postgres_loader.py's FakeConnection."""

    def __init__(self) -> None:
        self.licitaciones: dict[str, dict] = {}
        self.licitaciones_by_codigo: dict[str, int] = {}
        self.items: dict[str, dict] = {}
        self.organismos: dict[str, int] = {}
        self.categorias: dict[str, int] = {}
        self.licitacion_categoria_updates: dict[str, int] = {}
        self._next_organismo_id = 1
        self._next_categoria_id = 1
        self._next_licitacion_id = 1
        self.executed: list[str] = []
        self.closed = False
        self.committed = False
        self.rolled_back = False

    def seed_licitacion(self, codigo: str) -> int:
        licitacion_id = self._next_licitacion_id
        self._next_licitacion_id += 1
        self.licitaciones_by_codigo[codigo] = licitacion_id
        return licitacion_id

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append(sql)
        params = params or {}
        upper = sql.strip().upper()

        if upper.startswith("SELECT PAYLOAD_HASH FROM CORE.LICITACION"):
            row = self.licitaciones.get(params["natural_key"])
            return FakeResult([FakeRow(row["payload_hash"])] if row else [])
        if upper.startswith("SELECT ID FROM CORE.ORGANISMO"):
            organismo_id = self.organismos.get(params["codigo"])
            return FakeResult([FakeRow(organismo_id)] if organismo_id is not None else [])
        if upper.startswith("SELECT ID FROM CORE.LICITACION"):
            licitacion_id = self.licitaciones_by_codigo.get(params["codigo"])
            return FakeResult([FakeRow(licitacion_id)] if licitacion_id is not None else [])
        if upper.startswith("INSERT INTO CORE.ORGANISMO"):
            organismo_id = self._next_organismo_id
            self._next_organismo_id += 1
            self.organismos[params["codigo"]] = organismo_id
            return FakeResult([FakeRow(organismo_id)])
        if upper.startswith("SELECT ID FROM CORE.CATEGORIA"):
            categoria_id = self.categorias.get(params["codigo"])
            return FakeResult([FakeRow(categoria_id)] if categoria_id is not None else [])
        if upper.startswith("INSERT INTO CORE.CATEGORIA"):
            categoria_id = self._next_categoria_id
            self._next_categoria_id += 1
            self.categorias[params["codigo"]] = categoria_id
            return FakeResult([FakeRow(categoria_id)])
        if upper.startswith("UPDATE CORE.LICITACION SET CATEGORIA_ID"):
            self.licitacion_categoria_updates[params["codigo"]] = params["categoria_id"]
            return FakeResult([])
        if upper.startswith("INSERT INTO CORE.LICITACION_ITEM"):
            self.items[params["natural_key"]] = dict(params)
            return FakeResult([])
        if upper.startswith("INSERT INTO CORE.LICITACION"):
            self.licitaciones[params["natural_key"]] = dict(params)
            return FakeResult([])
        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def _run() -> IngestionRunContext:
    return IngestionRunContext(
        ingestion_run_id="run-1",
        source="chilecompra_api",
        resource="licitaciones",
        pipeline_version="0.1.0",
        started_at=datetime(2026, 8, 20, 12, 0, 0),
    )


def _record(codigo: str, payload_hash: str, **payload) -> TransformedRecord:
    return TransformedRecord(
        entity="licitacion",
        natural_key=f"chilecompra:licitacion:{codigo}",
        payload={"codigo": codigo, **payload},
        source_id=codigo,
        payload_hash=payload_hash,
    )


def test_load_inserts_new_licitacion() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionLoader(lambda: connection)

    result = loader.load(_run(), [_record("1000-1-LR26", "hash-a", nombre="Compra A")])

    assert isinstance(result, LoadResult)
    assert result.inserted == 1
    assert result.updated == 0
    assert result.unchanged == 0
    assert connection.licitaciones["chilecompra:licitacion:1000-1-LR26"]["nombre"] == "Compra A"
    assert connection.closed is True


def test_load_commits_the_transaction() -> None:
    """Regression: found against real data (6.13) — load() closed the
    connection without ever calling commit(), so a real Postgres
    connection silently rolled back every insert/update on close(). The
    old fake didn't track commit()/rollback() at all, so this was
    invisible to the test suite despite metrics reporting success."""
    connection = FakeConnection()
    loader = CoreLicitacionLoader(lambda: connection)

    loader.load(_run(), [_record("1000-1-LR26", "hash-a", nombre="Compra A")])

    assert connection.committed is True
    assert connection.rolled_back is False


def test_load_updates_when_payload_hash_changes() -> None:
    connection = FakeConnection()
    connection.licitaciones["chilecompra:licitacion:1000-1-LR26"] = {"payload_hash": "hash-old"}
    loader = CoreLicitacionLoader(lambda: connection)

    result = loader.load(_run(), [_record("1000-1-LR26", "hash-new", nombre="Compra A")])

    assert result.inserted == 0
    assert result.updated == 1
    assert result.unchanged == 0


def test_load_counts_unchanged_when_payload_hash_matches() -> None:
    connection = FakeConnection()
    connection.licitaciones["chilecompra:licitacion:1000-1-LR26"] = {"payload_hash": "hash-same"}
    loader = CoreLicitacionLoader(lambda: connection)

    result = loader.load(_run(), [_record("1000-1-LR26", "hash-same", nombre="Compra A")])

    assert result.inserted == 0
    assert result.updated == 0
    assert result.unchanged == 1


def test_load_without_agency_fields_leaves_organismo_unset() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionLoader(lambda: connection)

    loader.load(_run(), [_record("1000-1-LR26", "hash-a", nombre="Compra A")])

    stored = connection.licitaciones["chilecompra:licitacion:1000-1-LR26"]
    assert "organismo_id" not in stored
    assert connection.organismos == {}


def test_load_creates_organismo_when_agency_fields_present() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionLoader(lambda: connection)

    loader.load(
        _run(),
        [_record("1000-1-LR26", "hash-a", nombre="Compra A", agency_code="701", agency_name="Servicio Nacional")],
    )

    stored = connection.licitaciones["chilecompra:licitacion:1000-1-LR26"]
    assert stored["organismo_id"] == connection.organismos["701"]


def test_load_reuses_existing_organismo_across_licitaciones() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionLoader(lambda: connection)

    loader.load(
        _run(),
        [
            _record("1000-1-LR26", "hash-a", nombre="Compra A", agency_code="701", agency_name="Servicio Nacional"),
            _record("1000-2-LR26", "hash-b", nombre="Compra B", agency_code="701", agency_name="Servicio Nacional"),
        ],
    )

    first = connection.licitaciones["chilecompra:licitacion:1000-1-LR26"]["organismo_id"]
    second = connection.licitaciones["chilecompra:licitacion:1000-2-LR26"]["organismo_id"]
    assert first == second
    assert len(connection.organismos) == 1


def _item(correlativo: int, **overrides) -> LicitacionDetalleItem:
    defaults = dict(
        correlativo=correlativo, codigo_producto=11162110, codigo_categoria="11162100",
        categoria="Tejidos especiales", nombre_producto="Tul", descripcion="Linea N1",
        unidad_medida="Unidad", cantidad=1.0,
    )
    defaults.update(overrides)
    return LicitacionDetalleItem(**defaults)


def test_upsert_items_inserts_rows_for_known_licitacion() -> None:
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    loader = CoreLicitacionItemLoader(lambda: connection)

    upserted = loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26", items=[_item(1), _item(2, nombre_producto="Carretilla")],
    )

    assert upserted == 2
    assert len(connection.items) == 2
    stored = connection.items["chilecompra:licitacion_item:1002588-89-LE26:2"]
    assert stored["nombre"] == "Carretilla"


def test_upsert_items_skips_when_licitacion_unknown() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionItemLoader(lambda: connection)

    upserted = loader.upsert_items(connection, licitacion_codigo="unknown-codigo", items=[_item(1)])

    assert upserted == 0
    assert connection.items == {}


def test_upsert_items_returns_zero_for_empty_list() -> None:
    connection = FakeConnection()
    loader = CoreLicitacionItemLoader(lambda: connection)

    upserted = loader.upsert_items(connection, licitacion_codigo="1002588-89-LE26", items=[])

    assert upserted == 0
    assert connection.executed == []


def test_upsert_items_creates_categoria_and_links_it_to_the_item() -> None:
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    loader = CoreLicitacionItemLoader(lambda: connection)

    loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26",
        items=[_item(1, codigo_categoria="42192200", categoria="Sillas de ruedas")],
    )

    assert connection.categorias == {"42192200": 1}
    stored = connection.items["chilecompra:licitacion_item:1002588-89-LE26:1"]
    assert stored["categoria_id"] == 1


def test_upsert_items_reuses_an_existing_categoria_by_codigo() -> None:
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    connection.categorias["42192200"] = 7
    loader = CoreLicitacionItemLoader(lambda: connection)

    loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26",
        items=[_item(1, codigo_categoria="42192200")],
    )

    assert connection.categorias == {"42192200": 7}  # no duplicate created
    assert connection.items["chilecompra:licitacion_item:1002588-89-LE26:1"]["categoria_id"] == 7


def test_upsert_items_leaves_categoria_unset_when_the_item_has_none() -> None:
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    loader = CoreLicitacionItemLoader(lambda: connection)

    loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26",
        items=[_item(1, codigo_categoria=None, categoria=None)],
    )

    assert connection.categorias == {}
    assert connection.items["chilecompra:licitacion_item:1002588-89-LE26:1"]["categoria_id"] is None
    assert connection.licitacion_categoria_updates == {}


def test_upsert_items_sets_the_licitacion_to_its_most_common_item_categoria() -> None:
    """A tender with items in several rubros gets tagged with whichever rubro
    its items are mostly about — not the first or last one seen."""
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    loader = CoreLicitacionItemLoader(lambda: connection)

    loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26",
        items=[
            _item(1, codigo_categoria="42192200", categoria="Sillas de ruedas"),
            _item(2, codigo_categoria="42192200", categoria="Sillas de ruedas"),
            _item(3, codigo_categoria="53102500", categoria="Vestuario"),
        ],
    )

    dominant = connection.categorias["42192200"]
    assert connection.licitacion_categoria_updates["1002588-89-LE26"] == dominant


def test_upsert_items_does_not_touch_the_licitacion_when_no_item_has_a_categoria() -> None:
    connection = FakeConnection()
    connection.seed_licitacion("1002588-89-LE26")
    loader = CoreLicitacionItemLoader(lambda: connection)

    loader.upsert_items(
        connection, licitacion_codigo="1002588-89-LE26",
        items=[_item(1, codigo_categoria=None, categoria=None)],
    )

    assert connection.licitacion_categoria_updates == {}
