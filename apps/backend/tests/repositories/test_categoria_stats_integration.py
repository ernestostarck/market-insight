"""Real Postgres integration tests for categoria stats (backend support for a
real, non-simulated Categorías page: q/monto_minimo filters, and real award
stats computed from core.licitacion/core.adjudicacion).

Excluded from the default suite (`pytest -m integration -v`) — requires the dev
Postgres up with migrations at head.
"""

import asyncio
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.categoria import CategoriaRepository

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"
_TAG = "verify-categoria-stats"


@pytest.fixture
async def seeded_categorias():
    """Two rubros with different award volume/suppliers/buyers:

    - Sillas de Ruedas: 2 tenders, 2 awards to 2 different suppliers, 1 buyer.
    - Vestuario: 1 tender, 1 award, 1 supplier, 1 buyer, smaller amount.
    """
    engine = create_async_engine(_DATABASE_URL)
    async with engine.connect() as connection:
        organismo_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.organismo (source_system, natural_key, nombre) "
                    f"VALUES ('mercado_publico', '{_TAG}-org', 'Organismo {_TAG}') RETURNING id"
                )
            )
        ).scalar_one()

        categoria_ids: dict[str, int] = {}
        for nombre in ("Sillas de Ruedas", "Vestuario"):
            categoria_ids[nombre] = (
                await connection.execute(
                    text(
                        "INSERT INTO core.categoria (source_system, natural_key, codigo, nombre) "
                        "VALUES ('mercado_publico', :nk, :codigo, :nombre) RETURNING id"
                    ),
                    {"nk": f"{_TAG}-cat-{nombre}", "codigo": f"{_TAG}-{nombre}", "nombre": nombre},
                )
            ).scalar_one()

        proveedor_ids: dict[str, int] = {}
        for label, rut in (("Austral", "76111111-1"), ("Textil", "76222222-2")):
            proveedor_ids[label] = (
                await connection.execute(
                    text(
                        "INSERT INTO core.proveedor (source_system, natural_key, rut, razon_social) "
                        "VALUES ('mercado_publico', :nk, :rut, :razon_social) RETURNING id"
                    ),
                    {"nk": f"{_TAG}-prov-{label}", "rut": rut, "razon_social": f"{label} {_TAG}"},
                )
            ).scalar_one()

        licitacion_ids: list[int] = []
        adjudicacion_ids: list[int] = []

        async def _tender(categoria_nombre: str, index: str) -> int:
            licitacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, "
                        "organismo_id, categoria_id) VALUES ('mercado_publico', :nk, :codigo, :nombre, "
                        ":organismo_id, :categoria_id) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-lic-{index}", "codigo": f"{_TAG}-{index}",
                        "nombre": f"Licitacion {_TAG} {index}", "organismo_id": organismo_id,
                        "categoria_id": categoria_ids[categoria_nombre],
                    },
                )
            ).scalar_one()
            licitacion_ids.append(licitacion_id)
            return licitacion_id

        async def _award(licitacion_id: int, proveedor_label: str, monto: float, index: str) -> None:
            adjudicacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.adjudicacion (source_system, natural_key, licitacion_id, "
                        "proveedor_id, monto_adjudicado) VALUES ('mercado_publico', :nk, :licitacion_id, "
                        ":proveedor_id, :monto) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-adj-{index}", "licitacion_id": licitacion_id,
                        "proveedor_id": proveedor_ids[proveedor_label], "monto": monto,
                    },
                )
            ).scalar_one()
            adjudicacion_ids.append(adjudicacion_id)

        lic1 = await _tender("Sillas de Ruedas", "sr-1")
        await _award(lic1, "Austral", 1_000_000, "sr-1")
        lic2 = await _tender("Sillas de Ruedas", "sr-2")
        await _award(lic2, "Textil", 500_000, "sr-2")

        lic3 = await _tender("Vestuario", "vest-1")
        await _award(lic3, "Textil", 200_000, "vest-1")

        await connection.commit()

        try:
            yield categoria_ids
        finally:
            for adjudicacion_id in adjudicacion_ids:
                await connection.execute(
                    text("DELETE FROM core.adjudicacion WHERE id = :id"), {"id": adjudicacion_id}
                )
            for licitacion_id in licitacion_ids:
                await connection.execute(
                    text("DELETE FROM core.licitacion WHERE id = :id"), {"id": licitacion_id}
                )
            for proveedor_id in proveedor_ids.values():
                await connection.execute(
                    text("DELETE FROM core.proveedor WHERE id = :id"), {"id": proveedor_id}
                )
            for categoria_id in categoria_ids.values():
                await connection.execute(
                    text("DELETE FROM core.categoria WHERE id = :id"), {"id": categoria_id}
                )
            await connection.execute(text("DELETE FROM core.organismo WHERE id = :id"), {"id": organismo_id})
            await connection.commit()
    await engine.dispose()


async def test_stats_reflect_real_licitaciones_and_adjudicaciones(seeded_categorias) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        sillas = await CategoriaRepository(session).get_with_stats(seeded_categorias["Sillas de Ruedas"])

    assert sillas is not None
    assert sillas.total_licitaciones == 2
    assert sillas.monto_total == pytest.approx(1_500_000)
    assert sillas.total_proveedores == 2
    assert sillas.total_organismos == 1
    await engine.dispose()


async def test_filters_by_search_text(seeded_categorias) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await CategoriaRepository(session).get_page_filtered(limit=50, q=f"{_TAG}-Vestuario")

    assert {item.id for item in page.items} == {seeded_categorias["Vestuario"]}
    await engine.dispose()


async def test_filters_by_monto_minimo(seeded_categorias) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        # High limit: real award data now populates monto_total for ~1000+ real
        # categorias too, so a small page could miss our seeded one depending
        # on id ordering.
        page = await CategoriaRepository(session).get_page_filtered(limit=5000, monto_minimo=1_000_000)

    ids = {item.id for item in page.items}
    assert seeded_categorias["Sillas de Ruedas"] in ids
    assert seeded_categorias["Vestuario"] not in ids
    await engine.dispose()


async def test_top_proveedores_ranks_by_amount_and_computes_real_cuota(seeded_categorias) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        top = await CategoriaRepository(session).get_top_proveedores(seeded_categorias["Sillas de Ruedas"])

    assert [p.proveedor_nombre for p in top] == [f"Austral {_TAG}", f"Textil {_TAG}"]
    assert top[0].cuota == pytest.approx(66.7, abs=0.1)
    assert top[0].monto_adjudicado == pytest.approx(1_000_000)
    await engine.dispose()


async def test_top_organismos_includes_amount_and_tender_count(seeded_categorias) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        top = await CategoriaRepository(session).get_top_organismos(seeded_categorias["Sillas de Ruedas"])

    assert len(top) == 1
    assert top[0].total_licitaciones == 2
    assert top[0].monto_comprado == pytest.approx(1_500_000)
    await engine.dispose()


async def test_categoria_with_no_awards_has_zeroed_stats_not_missing_ones() -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with engine.connect() as connection:
        categoria_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.categoria (source_system, natural_key, codigo, nombre) "
                    f"VALUES ('mercado_publico', '{_TAG}-empty', 'empty-code', 'Sin Adjudicaciones') "
                    "RETURNING id"
                )
            )
        ).scalar_one()
        await connection.commit()
        try:
            async with async_sessionmaker(bind=engine)() as session:
                stats = await CategoriaRepository(session).get_with_stats(categoria_id)
            assert stats is not None
            assert stats.total_licitaciones == 0
            assert stats.monto_total == 0
            assert stats.total_proveedores == 0
            assert stats.total_organismos == 0
        finally:
            await connection.execute(text("DELETE FROM core.categoria WHERE id = :id"), {"id": categoria_id})
            await connection.commit()
    await engine.dispose()
