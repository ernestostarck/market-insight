"""Real Postgres integration test for CoreAdjudicacionLoader.upsert_from_items
— the real award data (proveedor/monto) lives nested per item under each
Items.Listado[].Adjudicacion in the licitacion detail payload, not in the
separate /adjudicaciones.json resource (confirmed empty against the real API:
every field but estado came back null).

Excluded from the default suite (`pytest -m integration -v`) — requires the dev
Postgres up with migrations at head.
"""

import asyncio
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text

from app.etl.loading.core_schema import CoreAdjudicacionLoader
from app.integrations.chilecompra.models import LicitacionDetalleItem

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"
_TAG = "verify-adjudicacion-loader"


@pytest.fixture
def seeded_licitacion():
    engine = create_engine(_DATABASE_URL)
    with engine.connect() as connection:
        organismo_id = connection.execute(
            text(
                "INSERT INTO core.organismo (source_system, natural_key, codigo, nombre) "
                f"VALUES ('mercado_publico', '{_TAG}-org', '{_TAG}-org-code', 'Organismo {_TAG}') "
                "RETURNING id"
            )
        ).scalar_one()
        licitacion_id = connection.execute(
            text(
                "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, organismo_id) "
                f"VALUES ('mercado_publico', '{_TAG}-lic', '{_TAG}-codigo', 'Licitacion {_TAG}', "
                f"{organismo_id}) RETURNING id"
            )
        ).scalar_one()
        connection.commit()
        try:
            yield {"licitacion_id": licitacion_id, "organismo_id": organismo_id}
        finally:
            connection.execute(
                text("DELETE FROM core.adjudicacion WHERE licitacion_id = :id"), {"id": licitacion_id}
            )
            connection.execute(text("DELETE FROM core.licitacion WHERE id = :id"), {"id": licitacion_id})
            connection.execute(text("DELETE FROM core.organismo WHERE id = :id"), {"id": organismo_id})
            for rut in ("76.555.555-5", "76.666.666-6"):
                proveedor_id = connection.execute(
                    text("SELECT id FROM core.proveedor WHERE rut = :rut"), {"rut": rut}
                ).first()
                if proveedor_id is not None:
                    connection.execute(
                        text("DELETE FROM core.proveedor WHERE id = :id"), {"id": proveedor_id[0]}
                    )
            connection.commit()
    engine.dispose()


def test_upsert_from_items_aggregates_multi_lot_award_by_proveedor(seeded_licitacion) -> None:
    engine = create_engine(_DATABASE_URL)
    loader = CoreAdjudicacionLoader(lambda: engine.connect())
    items = [
        LicitacionDetalleItem(
            correlativo=1, nombre_producto="Item 1",
            proveedor_rut="76.555.555-5", proveedor_nombre=f"Proveedor A {_TAG}",
            monto_unitario=100_000.0, cantidad_adjudicada=5.0,
        ),
        LicitacionDetalleItem(
            correlativo=2, nombre_producto="Item 2",
            proveedor_rut="76.555.555-5", proveedor_nombre=f"Proveedor A {_TAG}",
            monto_unitario=50_000.0, cantidad_adjudicada=2.0,
        ),
        LicitacionDetalleItem(
            correlativo=3, nombre_producto="Item 3",
            proveedor_rut="76.666.666-6", proveedor_nombre=f"Proveedor B {_TAG}",
            monto_unitario=200_000.0, cantidad_adjudicada=1.0,
        ),
    ]

    with engine.connect() as connection:
        upserted = loader.upsert_from_items(
            connection,
            licitacion_codigo=f"{_TAG}-codigo",
            monto_estimado=1_000_000.0,
            fecha_adjudicacion=datetime(2026, 3, 1, tzinfo=timezone.utc),
            numero_oferentes=4,
            items=items,
        )
        connection.commit()

    assert upserted == 2  # one row per distinct proveedor, not per item

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT p.razon_social, a.monto_adjudicado, a.monto_estimado, a.cantidad_ofertas, "
                "a.organismo_id, a.ratio_adjudicacion "
                "FROM core.adjudicacion a JOIN core.proveedor p ON p.id = a.proveedor_id "
                "WHERE a.licitacion_id = :id ORDER BY a.monto_adjudicado DESC"
            ),
            {"id": seeded_licitacion["licitacion_id"]},
        ).all()

    assert len(rows) == 2
    # Proveedor A: (100_000*5) + (50_000*2) = 600_000, across 2 lots
    assert rows[0].razon_social == f"Proveedor A {_TAG}"
    assert float(rows[0].monto_adjudicado) == pytest.approx(600_000.0)
    assert float(rows[0].ratio_adjudicacion) == pytest.approx(0.6)
    assert rows[0].cantidad_ofertas == 4
    assert rows[0].organismo_id == seeded_licitacion["organismo_id"]
    # Proveedor B: 200_000*1 = 200_000
    assert rows[1].razon_social == f"Proveedor B {_TAG}"
    assert float(rows[1].monto_adjudicado) == pytest.approx(200_000.0)
    engine.dispose()


def test_upsert_from_items_skips_unknown_licitacion() -> None:
    engine = create_engine(_DATABASE_URL)
    loader = CoreAdjudicacionLoader(lambda: engine.connect())
    items = [
        LicitacionDetalleItem(
            correlativo=1, proveedor_rut="76.555.555-5", proveedor_nombre="x",
            monto_unitario=1.0, cantidad_adjudicada=1.0,
        ),
    ]

    with engine.connect() as connection:
        upserted = loader.upsert_from_items(
            connection,
            licitacion_codigo=f"{_TAG}-no-such-codigo",
            monto_estimado=None,
            fecha_adjudicacion=None,
            numero_oferentes=None,
            items=items,
        )

    assert upserted == 0
    engine.dispose()


def test_upsert_from_items_skips_items_without_real_proveedor(seeded_licitacion) -> None:
    """Not every closed tender's detail has award data populated by
    ChileCompra yet — items with no proveedor_rut must not create a row."""
    engine = create_engine(_DATABASE_URL)
    loader = CoreAdjudicacionLoader(lambda: engine.connect())
    items = [LicitacionDetalleItem(correlativo=1, nombre_producto="Item sin adjudicar")]

    with engine.connect() as connection:
        upserted = loader.upsert_from_items(
            connection,
            licitacion_codigo=f"{_TAG}-codigo",
            monto_estimado=None,
            fecha_adjudicacion=None,
            numero_oferentes=None,
            items=items,
        )

    assert upserted == 0
    engine.dispose()
