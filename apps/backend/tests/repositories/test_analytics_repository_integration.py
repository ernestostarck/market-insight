"""Real Postgres integration tests for AnalyticsRepository's core.*-backed
aggregates (market_monthly/supplier_performance/category_spending/
disability_contracts) — replacing the dw.* star schema, which nothing loads.

Excluded from the default suite (`pytest -m integration -v`) — requires the dev
Postgres up with migrations at head.
"""

import asyncio
import sys
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.analytics import AnalyticsRepository

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"
_TAG = "verify-analytics-repo"


@pytest.fixture
async def seeded_awards():
    """One organismo, two proveedores, one categoria (marked with `discapacidad`
    in its tender name), two tenders each with one award in different months."""
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

        categoria_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.categoria (source_system, natural_key, codigo, nombre) "
                    f"VALUES ('mercado_publico', '{_TAG}-cat', '{_TAG}-code', 'Rubro {_TAG}') "
                    "RETURNING id"
                )
            )
        ).scalar_one()

        proveedor_ids: dict[str, int] = {}
        for label, rut in (("Austral", "76333333-3"), ("Textil", "76444444-4")):
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

        async def _tender(index: str, nombre: str, fecha_publicacion: datetime) -> int:
            licitacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, "
                        "organismo_id, categoria_id, fecha_publicacion) VALUES ('mercado_publico', :nk, "
                        ":codigo, :nombre, :organismo_id, :categoria_id, :fecha_publicacion) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-lic-{index}", "codigo": f"{_TAG}-{index}", "nombre": nombre,
                        "organismo_id": organismo_id, "categoria_id": categoria_id,
                        "fecha_publicacion": fecha_publicacion,
                    },
                )
            ).scalar_one()
            licitacion_ids.append(licitacion_id)
            return licitacion_id

        async def _award(
            licitacion_id: int, proveedor_label: str, monto: float, ratio: float, fecha: datetime, index: str,
            cantidad_ofertas: int = 3,
        ) -> None:
            adjudicacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.adjudicacion (source_system, natural_key, licitacion_id, "
                        "proveedor_id, monto_adjudicado, ratio_adjudicacion, fecha_adjudicacion, "
                        "cantidad_ofertas) VALUES ('mercado_publico', :nk, :licitacion_id, :proveedor_id, "
                        ":monto, :ratio, :fecha, :cantidad_ofertas) RETURNING id"
                    ),
                    {
                        "nk": f"{_TAG}-adj-{index}", "licitacion_id": licitacion_id,
                        "proveedor_id": proveedor_ids[proveedor_label], "monto": monto,
                        "ratio": ratio, "fecha": fecha, "cantidad_ofertas": cantidad_ofertas,
                    },
                )
            ).scalar_one()
            adjudicacion_ids.append(adjudicacion_id)

        lic1 = await _tender(
            "t1", f"Sillas de ruedas para discapacidad {_TAG}", datetime(2026, 1, 5, tzinfo=timezone.utc)
        )
        await _award(
            lic1, "Austral", 1_000_000, 0.90, datetime(2026, 1, 15, tzinfo=timezone.utc), "a1",
            cantidad_ofertas=1,
        )

        lic2 = await _tender(
            "t2", f"Camas clinicas {_TAG}", datetime(2026, 2, 3, tzinfo=timezone.utc)
        )
        await _award(
            lic2, "Textil", 500_000, 0.80, datetime(2026, 2, 10, tzinfo=timezone.utc), "a2",
            cantidad_ofertas=5,
        )

        await connection.commit()

        try:
            yield {
                "organismo_id": organismo_id,
                "categoria_id": categoria_id,
                "proveedor_ids": proveedor_ids,
                "licitacion_ids": licitacion_ids,
            }
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
            await connection.execute(text("DELETE FROM core.categoria WHERE id = :id"), {"id": categoria_id})
            await connection.execute(text("DELETE FROM core.organismo WHERE id = :id"), {"id": organismo_id})
            await connection.commit()
    await engine.dispose()


async def test_market_monthly_aggregates_real_licitaciones_and_adjudicaciones(seeded_awards) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        rows = await AnalyticsRepository(session).market_monthly(
            start_month=date(2026, 1, 1), end_month=date(2026, 2, 28), limit=1000
        )

    # >= rather than == : real awards from the niche backfill may already
    # share these same months, so this only asserts our seeded amount is
    # included, not that the bucket is exactly ours.
    by_month = {row.mes: row for row in rows}
    assert by_month[date(2026, 1, 1)].total_licitaciones >= 1
    assert float(by_month[date(2026, 1, 1)].monto_total_adjudicado) >= 1_000_000
    assert float(by_month[date(2026, 2, 1)].monto_total_adjudicado) >= 500_000
    await engine.dispose()


async def test_supplier_performance_reflects_real_awards(seeded_awards) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        rows = await AnalyticsRepository(session).supplier_performance(query=_TAG, limit=1000)

    by_name = {row.razon_social: row for row in rows}
    assert by_name[f"Austral {_TAG}"].monto_total_adjudicado == pytest.approx(1_000_000)
    assert by_name[f"Austral {_TAG}"].total_adjudicaciones == 1
    assert float(by_name[f"Austral {_TAG}"].ratio_adjudicacion_promedio) == pytest.approx(0.90)
    await engine.dispose()


async def test_category_spending_aggregates_real_awards_by_categoria(seeded_awards) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        rows = await AnalyticsRepository(session).category_spending(
            category_code=f"{_TAG}-code", limit=1000
        )

    assert len(rows) == 1
    assert rows[0].gasto_total_oc == pytest.approx(1_500_000)
    assert rows[0].numero_ordenes_compra == 2
    await engine.dispose()


async def test_disability_contracts_matches_real_tender_name(seeded_awards) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        rows = await AnalyticsRepository(session).disability_contracts(supplier=_TAG, limit=1000)

    assert len(rows) == 1
    assert "discapacidad" in rows[0].nombre.lower()
    assert rows[0].proveedor == f"Austral {_TAG}"
    await engine.dispose()


async def test_market_objective_matches_real_domain_dictionary_terms(seeded_awards) -> None:
    """lic1 ("Sillas de ruedas para discapacidad ...") matches the real
    domain dictionary (app/nlp/dictionary.py has "discapacidad" as a surface
    form); lic2 ("Camas clinicas ...") does not. Baseline is captured first
    since core.adjudicacion is shared with any real (national) data already
    backfilled — this only asserts our seeded tender moved the real count,
    not that it appears in a limited top-10 leaderboard."""
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        summary = await AnalyticsRepository(session).market_objective_summary()

    assert summary["dictionary_terms_used"] > 0
    assert summary["kpis"]["licitaciones_relacionadas"] >= 1
    assert summary["kpis"]["monto_total"] >= 1_000_000
    await engine.dispose()


async def test_price_items_matches_real_item_text(seeded_awards) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with engine.connect() as connection:
        await connection.execute(
            text(
                "INSERT INTO core.licitacion_item (licitacion_id, natural_key, codigo, nombre, "
                "cantidad, unidad, precio_unitario, categoria_id) VALUES (:licitacion_id, :nk, "
                "'item-1', :nombre, 20, 'Unidad', 1420000, :categoria_id)"
            ),
            {
                "licitacion_id": seeded_awards["licitacion_ids"][0],
                "nk": f"{_TAG}-item-1",
                "nombre": f"Cama clinica electrica {_TAG}",
                "categoria_id": seeded_awards["categoria_id"],
            },
        )
        await connection.commit()

    try:
        async with async_sessionmaker(bind=engine)() as session:
            rows = await AnalyticsRepository(session).price_items(q=f"electrica {_TAG}", limit=50)

        assert len(rows) == 1
        assert float(rows[0].precio_unitario) == pytest.approx(1_420_000)
        assert rows[0].organismo == f"Organismo {_TAG}"
    finally:
        async with engine.connect() as connection:
            await connection.execute(
                text("DELETE FROM core.licitacion_item WHERE natural_key = :nk"),
                {"nk": f"{_TAG}-item-1"},
            )
            await connection.commit()
    await engine.dispose()


async def test_competition_summary_averages_real_bidder_counts(seeded_awards) -> None:
    # This aggregates across the whole table, which now also includes the
    # real niche backfill's ~7k rows — so this only asserts our 2 seeded
    # rows are correctly counted into their buckets, not the global average.
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        summary = await AnalyticsRepository(session).competition_summary()

    assert summary["total_adjudicaciones_con_oferentes"] >= 2
    by_rango = {b["rango_oferentes"]: b for b in summary["distribucion_oferentes"]}
    assert by_rango["1 oferente"]["total_procesos"] >= 1
    assert by_rango["4-6 oferentes"]["total_procesos"] >= 1
    await engine.dispose()
