"""Real Postgres integration tests for proveedor filtering and stats (backend support
for the /proveedores filter bar: q, region, rubro, tasa_minima).

Excluded from the default suite (`pytest -m integration -v`) — requires the dev
Postgres up with migrations at head.
"""

import asyncio
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.proveedor import ProveedorRepository

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"
_TAG = "verify-proveedor-filters"


@pytest.fixture
async def seeded_proveedores():
    """Two proveedores with different regions/categories/success rates:

    - Austral (Metropolitana): 4 ofertas, 3 awards (75%), mostly "Camas Clinicas".
    - Sur (Biobio): 4 ofertas, 1 award (25%), category "Sillas de Ruedas".
    - Nuevo (Valparaiso): registered, never bid (0 ofertas, tasa_exito must be None).
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

        categoria_ids = {}
        for nombre in ("Camas Clinicas", "Sillas de Ruedas"):
            categoria_ids[nombre] = (
                await connection.execute(
                    text(
                        "INSERT INTO core.categoria (source_system, natural_key, nombre) "
                        "VALUES ('mercado_publico', :nk, :nombre) RETURNING id"
                    ),
                    {"nk": f"{_TAG}-cat-{nombre}", "nombre": nombre},
                )
            ).scalar_one()

        proveedor_ids = {}
        for label, region, rut in (
            ("Austral", "Metropolitana de Santiago", "76111111-1"),
            ("Sur", "Biobio", "76222222-2"),
            ("Nuevo", "Valparaiso", "76333333-3"),
        ):
            proveedor_ids[label] = (
                await connection.execute(
                    text(
                        "INSERT INTO core.proveedor (source_system, natural_key, rut, razon_social, region) "
                        "VALUES ('mercado_publico', :nk, :rut, :razon_social, :region) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-prov-{label}",
                        "rut": rut,
                        "razon_social": f"{label} Equipos Medicos {_TAG}",
                        "region": region,
                    },
                )
            ).scalar_one()

        licitacion_ids: list[int] = []
        oferta_ids: list[int] = []
        adjudicacion_ids: list[int] = []

        async def _make_licitacion(categoria_nombre: str, index: int) -> int:
            licitacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, categoria_id) "
                        "VALUES ('mercado_publico', :nk, :codigo, :nombre, :categoria_id) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-lic-{index}",
                        "codigo": f"{_TAG}-{index}",
                        "nombre": f"Licitacion {_TAG} {index}",
                        "categoria_id": categoria_ids[categoria_nombre],
                    },
                )
            ).scalar_one()
            licitacion_ids.append(licitacion_id)
            return licitacion_id

        async def _bid(proveedor_label: str, licitacion_id: int, monto: float, awarded: bool, index: int) -> None:
            oferta_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.oferta (source_system, natural_key, licitacion_id, proveedor_id, "
                        "monto, es_adjudicada) VALUES ('mercado_publico', :nk, :licitacion_id, :proveedor_id, "
                        ":monto, :awarded) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-oferta-{index}",
                        "licitacion_id": licitacion_id,
                        "proveedor_id": proveedor_ids[proveedor_label],
                        "monto": monto,
                        "awarded": awarded,
                    },
                )
            ).scalar_one()
            oferta_ids.append(oferta_id)
            if awarded:
                adjudicacion_id = (
                    await connection.execute(
                        text(
                            "INSERT INTO core.adjudicacion (source_system, natural_key, licitacion_id, "
                            "proveedor_id, monto_adjudicado) VALUES ('mercado_publico', :nk, :licitacion_id, "
                            ":proveedor_id, :monto) RETURNING id"
                        ),
                        {
                            "nk": f"{_TAG}-adj-{index}",
                            "licitacion_id": licitacion_id,
                            "proveedor_id": proveedor_ids[proveedor_label],
                            "monto": monto,
                        },
                    )
                ).scalar_one()
                adjudicacion_ids.append(adjudicacion_id)

        # Austral: 3 licitaciones in "Camas Clinicas" (awarded) + 1 in "Sillas de Ruedas" (not awarded).
        for i in range(3):
            lic = await _make_licitacion("Camas Clinicas", f"austral-cc-{i}")
            await _bid("Austral", lic, monto=1_000_000 + i, awarded=True, index=f"austral-cc-{i}")
        lic = await _make_licitacion("Sillas de Ruedas", "austral-sr-0")
        await _bid("Austral", lic, monto=500_000, awarded=False, index="austral-sr-0")

        # Sur: 4 licitaciones in "Sillas de Ruedas", only 1 awarded (25%).
        for i in range(4):
            lic = await _make_licitacion("Sillas de Ruedas", f"sur-sr-{i}")
            await _bid("Sur", lic, monto=200_000, awarded=(i == 0), index=f"sur-sr-{i}")

        await connection.commit()

        try:
            yield proveedor_ids
        finally:
            for adjudicacion_id in adjudicacion_ids:
                await connection.execute(
                    text("DELETE FROM core.adjudicacion WHERE id = :id"), {"id": adjudicacion_id}
                )
            for oferta_id in oferta_ids:
                await connection.execute(text("DELETE FROM core.oferta WHERE id = :id"), {"id": oferta_id})
            for licitacion_id in licitacion_ids:
                await connection.execute(
                    text("DELETE FROM core.licitacion WHERE id = :id"), {"id": licitacion_id}
                )
            for proveedor_id in proveedor_ids.values():
                await connection.execute(
                    text("DELETE FROM core.proveedor WHERE id = :id"), {"id": proveedor_id}
                )
            await connection.execute(
                text("DELETE FROM core.categoria WHERE natural_key LIKE :pattern"),
                {"pattern": f"{_TAG}-cat-%"},
            )
            await connection.execute(text("DELETE FROM core.organismo WHERE id = :id"), {"id": organismo_id})
            await connection.commit()
    await engine.dispose()


async def test_filters_by_region(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(limit=50, region="Biobio")

    ids = {item.id for item in page.items}
    assert seeded_proveedores["Sur"] in ids
    assert seeded_proveedores["Austral"] not in ids
    assert seeded_proveedores["Nuevo"] not in ids
    await engine.dispose()


async def test_filters_by_search_text_on_razon_social(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(
            limit=50, q=f"Sur Equipos Medicos {_TAG}"
        )

    assert {item.id for item in page.items} == {seeded_proveedores["Sur"]}
    await engine.dispose()


async def test_filters_by_rubro_using_the_most_common_award_category(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(limit=50, rubro="Camas Clinicas")

    ids = {item.id for item in page.items}
    assert seeded_proveedores["Austral"] in ids
    assert seeded_proveedores["Sur"] not in ids
    await engine.dispose()


async def test_filters_by_tasa_minima_and_excludes_bidders_with_no_participation(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(limit=50, tasa_minima=50)

    ids = {item.id for item in page.items}
    assert seeded_proveedores["Austral"] in ids  # 75%
    assert seeded_proveedores["Sur"] not in ids  # 25%
    assert seeded_proveedores["Nuevo"] not in ids  # never bid -> tasa_exito is None
    await engine.dispose()


async def test_computed_stats_are_correct(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = ProveedorRepository(session)
        austral = await repository.get_with_stats(seeded_proveedores["Austral"])
        nuevo = await repository.get_with_stats(seeded_proveedores["Nuevo"])

    assert austral is not None
    assert austral.total_licitaciones_participadas == 4
    assert austral.total_adjudicaciones == 3
    assert austral.tasa_exito == pytest.approx(75.0)
    assert austral.monto_total_adjudicado == pytest.approx(3_000_003.0)
    assert austral.categoria_principal == "Camas Clinicas"
    assert austral.region == "Metropolitana de Santiago"

    assert nuevo is not None
    assert nuevo.total_licitaciones_participadas == 0
    assert nuevo.total_adjudicaciones == 0
    assert nuevo.tasa_exito is None
    assert nuevo.categoria_principal is None
    await engine.dispose()


async def test_combining_filters_narrows_further(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(
            limit=50, region="Metropolitana de Santiago", tasa_minima=50
        )

    assert {item.id for item in page.items} == {seeded_proveedores["Austral"]}
    await engine.dispose()


async def test_unfiltered_page_still_reports_stats_for_every_proveedor(seeded_proveedores) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        page = await ProveedorRepository(session).get_page_filtered(limit=200)

    by_id = {item.id: item for item in page.items}
    assert by_id[seeded_proveedores["Austral"]].total_adjudicaciones == 3
    assert by_id[seeded_proveedores["Sur"]].total_adjudicaciones == 1
    assert by_id[seeded_proveedores["Nuevo"]].total_adjudicaciones == 0
    await engine.dispose()
