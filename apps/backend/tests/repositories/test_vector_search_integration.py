"""Real Postgres + pgvector integration tests (Fase 6.9).

Excluded from the default suite (`pytest -m integration -v` to run them) —
requires the dev Postgres up (`docker compose up -d postgres`) with
migrations at head (the 6.9 HNSW index in particular).
"""

import asyncio
import sys
import uuid

import numpy as np
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.repositories.vector_search import VectorSearchRepository

pytestmark = pytest.mark.integration

if sys.platform == "win32":
    # psycopg's async mode can't run on Windows' default ProactorEventLoop.
    # Production always runs inside Linux Docker (no Proactor there) — this
    # only matters for running this test directly on a Windows dev host.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_DATABASE_URL = "postgresql+psycopg://market_insight:market_insight_dev@127.0.0.1:5432/market_insight"


def _vector(*values: float, dimensions: int = 384) -> np.ndarray:
    padded = list(values) + [0.0] * (dimensions - len(values))
    return np.array(padded, dtype=np.float32)


@pytest.fixture
async def seeded_licitaciones():
    engine = create_async_engine(_DATABASE_URL)
    async with engine.connect() as connection:
        organismo_id = (
            await connection.execute(
                text(
                    "INSERT INTO core.organismo (source_system, natural_key, nombre) "
                    "VALUES ('mercado_publico', 'org-verify-6.9', 'Organismo verificacion 6.9') RETURNING id"
                )
            )
        ).scalar_one()

        model_version_id = uuid.uuid4()
        await connection.execute(
            text(
                "INSERT INTO knowledge.model_versions (id, name, version, kind, status) "
                "VALUES (:id, 'test-model-6.9', 'v1', 'embedding', 'production')"
            ),
            {"id": model_version_id},
        )

        licitacion_ids: dict[str, int] = {}
        vectors = {
            "identical": _vector(1.0),
            "related": _vector(0.8, 0.6),
            "unrelated": _vector(0.0, 1.0),
        }
        for label, vector in vectors.items():
            licitacion_id = (
                await connection.execute(
                    text(
                        "INSERT INTO core.licitacion (source_system, natural_key, codigo, nombre, organismo_id) "
                        "VALUES ('mercado_publico', :natural_key, :codigo, :nombre, :organismo_id) RETURNING id"
                    ),
                    {
                        "natural_key": f"lic-verify-6.9-{label}", "codigo": f"VERIFY-6.9-{label}",
                        "nombre": f"Licitacion {label}", "organismo_id": organismo_id,
                    },
                )
            ).scalar_one()
            licitacion_ids[label] = licitacion_id
            vector_literal = "[" + ",".join(f"{v:.8f}" for v in vector.tolist()) + "]"
            await connection.execute(
                text(
                    "INSERT INTO knowledge.embeddings (id, licitacion_id, model_version_id, content_hash, text, vector) "
                    "VALUES (:id, :licitacion_id, :model_version_id, :content_hash, 'texto de prueba', :vector)"
                ),
                {
                    "id": uuid.uuid4(), "licitacion_id": licitacion_id, "model_version_id": model_version_id,
                    "content_hash": f"hash-{label}", "vector": vector_literal,
                },
            )
        await connection.commit()

        try:
            yield licitacion_ids
        finally:
            await connection.execute(
                text("DELETE FROM knowledge.embeddings WHERE licitacion_id = ANY(:ids)"),
                {"ids": list(licitacion_ids.values())},
            )
            await connection.execute(
                text("DELETE FROM core.licitacion WHERE id = ANY(:ids)"), {"ids": list(licitacion_ids.values())},
            )
            await connection.execute(text("DELETE FROM core.organismo WHERE natural_key = 'org-verify-6.9'"))
            await connection.execute(
                text("DELETE FROM knowledge.model_versions WHERE id = :id"), {"id": model_version_id},
            )
            await connection.commit()
    await engine.dispose()


async def test_search_by_vector_ranks_by_cosine_similarity_descending(seeded_licitaciones) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = VectorSearchRepository(session)
        results = await repository.search_by_vector(_vector(1.0), top_k=10, min_similarity=0.0)

    by_label = {lid: label for label, lid in seeded_licitaciones.items()}
    ours = [r for r in results if r.licitacion_id in by_label]
    assert [by_label[r.licitacion_id] for r in ours] == ["identical", "related", "unrelated"]
    assert ours[0].similarity == pytest.approx(1.0, abs=1e-4)
    assert ours[1].similarity == pytest.approx(0.8, abs=1e-4)
    assert ours[2].similarity == pytest.approx(0.0, abs=1e-4)
    await engine.dispose()


async def test_search_by_vector_respects_min_similarity_threshold(seeded_licitaciones) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = VectorSearchRepository(session)
        results = await repository.search_by_vector(_vector(1.0), top_k=10, min_similarity=0.5)

    by_label = {lid: label for label, lid in seeded_licitaciones.items()}
    ours = [r for r in results if r.licitacion_id in by_label]
    assert {by_label[r.licitacion_id] for r in ours} == {"identical", "related"}
    await engine.dispose()


async def test_search_by_vector_respects_top_k(seeded_licitaciones) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = VectorSearchRepository(session)
        results = await repository.search_by_vector(_vector(1.0), top_k=1, min_similarity=0.0)

    assert len(results) == 1


async def test_find_similar_to_licitacion_excludes_itself(seeded_licitaciones) -> None:
    engine = create_async_engine(_DATABASE_URL)
    async with async_sessionmaker(bind=engine)() as session:
        repository = VectorSearchRepository(session)
        results = await repository.find_similar_to_licitacion(
            seeded_licitaciones["identical"], top_k=10, min_similarity=0.0,
        )

    assert all(r.licitacion_id != seeded_licitaciones["identical"] for r in results)
    by_label = {lid: label for label, lid in seeded_licitaciones.items()}
    ours = [r for r in results if r.licitacion_id in by_label]
    assert [by_label[r.licitacion_id] for r in ours] == ["related", "unrelated"]
    await engine.dispose()
