"""Real Postgres full-text search integration tests (Fase 6.10).

Excluded from the default suite (`pytest -m integration -v`) — requires
the dev Postgres up with migrations at head (the 6.10 tsvector/GIN columns
in particular).
"""

import asyncio
import sys
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.hybrid_search import HybridSearchRepository

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"


@pytest.fixture
async def seeded_licitacion():
    engine = create_async_engine(_DATABASE_URL)
    async with engine.connect() as connection:
        organismo_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.organismo (source_system, natural_key, nombre) "
                    "VALUES ('mercado_publico', 'org-verify-6.10', 'Organismo verificacion 6.10') RETURNING id"
                )
            )
        ).scalar_one()
        licitacion_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, descripcion, organismo_id) "
                    "VALUES ('mercado_publico', 'lic-verify-6.10', 'VERIFY-6.10', "
                    "'Adquisicion de sillas de ruedas', 'Compra de sillas de ruedas plegables para adultos mayores', :organismo_id) "
                    "RETURNING id"
                ),
                {"organismo_id": organismo_id},
            )
        ).scalar_one()
        item_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.licitacion_item (licitacion_id, nombre, descripcion, natural_key) "
                    "VALUES (:licitacion_id, 'Rampa de acceso', 'Rampa metalica para accesibilidad', 'item-verify-6.10') "
                    "RETURNING id"
                ),
                {"licitacion_id": licitacion_id},
            )
        ).scalar_one()
        await connection.commit()

        try:
            yield licitacion_id
        finally:
            await connection.execute(text("DELETE FROM core.licitacion_item WHERE id = :id"), {"id": item_id})
            await connection.execute(text("DELETE FROM core.licitacion WHERE id = :id"), {"id": licitacion_id})
            await connection.execute(text("DELETE FROM core.organismo WHERE natural_key = 'org-verify-6.10'"))
            await connection.commit()
    await engine.dispose()


async def test_search_fulltext_stems_spanish_plural_to_singular(seeded_licitacion) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = HybridSearchRepository(session)
        results = await repository.search_fulltext("silla")

    assert any(r.licitacion_id == seeded_licitacion for r in results)
    await engine.dispose()


async def test_search_fulltext_finds_nothing_unrelated(seeded_licitacion) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = HybridSearchRepository(session)
        results = await repository.search_fulltext("notebook licencias oficina")

    assert not any(r.licitacion_id == seeded_licitacion for r in results)
    await engine.dispose()


async def test_search_products_finds_licitacion_via_item_text(seeded_licitacion) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = HybridSearchRepository(session)
        results = await repository.search_products("rampa accesibilidad")

    assert any(r.licitacion_id == seeded_licitacion for r in results)
    await engine.dispose()


async def test_search_by_code_matches_exact_and_prefix(seeded_licitacion) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = HybridSearchRepository(session)
        exact = await repository.search_by_code("VERIFY-6.10")
        prefix = await repository.search_by_code("VERIFY-6")

    assert any(r.licitacion_id == seeded_licitacion for r in exact)
    assert any(r.licitacion_id == seeded_licitacion for r in prefix)
    await engine.dispose()
