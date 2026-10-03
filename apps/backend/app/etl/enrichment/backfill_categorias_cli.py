"""One-off backfill: re-run detail enrichment for licitaciones that already
have items, so `core.categoria` gets populated with ChileCompra's own rubro
data (`CodigoCategoria`/`Categoria`) via `CoreLicitacionItemLoader` (added
after these licitaciones were first enriched — see docs/07-ai/taxonomy.md).

Deliberately scoped to licitaciones that were already enriched once (already
have `core.licitacion_item` rows), not the whole `core.licitacion` table:
enrichment calls ChileCompra's detail endpoint per licitacion, and the
project's own design keeps that off any bulk/scheduled path to avoid
multiplying daily API volume (see licitacion_detail.py's module docstring).
This is a manual, explicit, one-time exception to seed real data instead of
leaving core.categoria empty or simulating rows.

Run inside a container with the real ChileCompra ticket and DB host (the
`etl-worker` service, or `backend`):

    docker compose exec etl-worker python -m app.etl.enrichment.backfill_categorias_cli
"""

from __future__ import annotations

import asyncio

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.etl.enrichment.licitacion_detail import enrich_licitacion_detail
from app.etl.loading.core_schema import CoreLicitacionItemLoader, CoreLicitacionLoader
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.sdk import ChileCompraClient as ChileCompraSDK

_DELAY_SECONDS = 0.4


def _already_enriched_codigos(engine) -> list[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT DISTINCT l.codigo FROM core.licitacion l "
                "JOIN core.licitacion_item li ON li.licitacion_id = l.id "
                "ORDER BY l.codigo"
            )
        ).all()
    return [row[0] for row in rows]


async def _run() -> None:
    settings = get_settings()
    if not settings.chilecompra_api_ticket:
        raise SystemExit(
            "CHILECOMPRA_API_TICKET is not set in this environment — run this inside "
            "a container that loads docker/compose/.env.backend (etl-worker or backend)."
        )

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    client = ChileCompraSDK.from_config(ChileCompraConfig.from_settings())
    licitacion_loader = CoreLicitacionLoader(lambda: engine.connect())
    item_loader = CoreLicitacionItemLoader(lambda: engine.connect())

    codigos = _already_enriched_codigos(engine)
    print(f"Backfilling categoria for {len(codigos)} already-enriched licitaciones...")

    found = failed = with_categoria = 0
    for index, codigo in enumerate(codigos, start=1):
        try:
            result = await enrich_licitacion_detail(
                codigo, client=client, licitacion_loader=licitacion_loader,
                item_loader=item_loader, connection_factory=lambda: engine.connect(),
            )
            found += int(result.found)
            print(f"[{index}/{len(codigos)}] {codigo}: found={result.found} items_upserted={result.items_upserted}")
        except Exception as exc:  # noqa: BLE001 - one bad codigo must not abort the batch
            failed += 1
            print(f"[{index}/{len(codigos)}] {codigo}: FAILED ({exc})")
        await asyncio.sleep(_DELAY_SECONDS)

    with engine.connect() as connection:
        with_categoria = connection.scalar(
            text("SELECT count(*) FROM core.licitacion WHERE categoria_id IS NOT NULL")
        )
        categoria_rows = connection.scalar(text("SELECT count(*) FROM core.categoria"))

    print(
        f"\nDone: {found} found, {failed} failed, "
        f"{with_categoria} licitaciones now have categoria_id, "
        f"{categoria_rows} rows in core.categoria."
    )


if __name__ == "__main__":
    asyncio.run(_run())
