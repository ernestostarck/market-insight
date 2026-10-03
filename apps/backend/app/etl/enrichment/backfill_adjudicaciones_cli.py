"""One-off backfill: populate `core.adjudicacion`/`core.proveedor` for the
geriatría/discapacidad niche by re-running detail enrichment
(`enrich_licitacion_detail`, already used for categoria) with its
`adjudicacion_loader` wired in.

Real award data (winning proveedor, unit price) lives nested per item under
`Items.Listado[].Adjudicacion` in the licitacion detail payload — NOT in the
separate `/adjudicaciones.json` resource. Verified against the real API: a
national by-date bulk pull from that endpoint (6,208 real licitaciones
matched) came back with every field but `estado` null — it only reports
status changes, no proveedor or monto. See CoreAdjudicacionLoader's docstring.

Scoped to licitaciones matching the real geriatría/discapacidad domain
dictionary (app/nlp/dictionary.py) AND estado='8' (Adjudicada) — ~4,176 of
them, vs. ~11,663 nationally. This is what Market Objective/Analytics need;
a full national backfill is a separate, much larger decision.

Run inside a container with the real ChileCompra ticket and DB host (the
`etl-worker` service, or `backend`):

    docker compose exec etl-worker python -m app.etl.enrichment.backfill_adjudicaciones_cli
"""

from __future__ import annotations

import asyncio

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.etl.loading.core_schema import (
    CoreAdjudicacionLoader,
    CoreLicitacionItemLoader,
    CoreLicitacionLoader,
)
from app.etl.enrichment.licitacion_detail import enrich_licitacion_detail
from app.integrations.chilecompra.config import ChileCompraConfig
from app.integrations.chilecompra.sdk import ChileCompraClient as ChileCompraSDK
from app.nlp.dictionary import load_initial_dictionary

_DELAY_SECONDS = 0.4


def _niche_codigos_adjudicadas(engine, *, skip_already_loaded: bool = True) -> list[str]:
    dictionary = load_initial_dictionary()
    terms = sorted({f.strip().lower() for e in dictionary.entries for f in e.all_surface_forms()})
    conditions = " OR ".join(f"nombre ILIKE :t{i} OR descripcion ILIKE :t{i}" for i in range(len(terms)))
    params = {f"t{i}": f"%{t}%" for i, t in enumerate(terms)}

    already_loaded_clause = (
        "AND l.id NOT IN (SELECT DISTINCT licitacion_id FROM core.adjudicacion) "
        if skip_already_loaded
        else ""
    )
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"SELECT l.codigo FROM core.licitacion l WHERE l.estado = '8' {already_loaded_clause}"
                f"AND ({conditions}) ORDER BY l.codigo"
            ),
            params,
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
    adjudicacion_loader = CoreAdjudicacionLoader(lambda: engine.connect())

    codigos = _niche_codigos_adjudicadas(engine)
    print(f"Backfilling real awards for {len(codigos)} niche licitaciones (estado=Adjudicada)...")

    found = failed = with_award = 0
    for index, codigo in enumerate(codigos, start=1):
        try:
            result = await enrich_licitacion_detail(
                codigo,
                client=client,
                licitacion_loader=licitacion_loader,
                item_loader=item_loader,
                connection_factory=lambda: engine.connect(),
                adjudicacion_loader=adjudicacion_loader,
            )
            found += int(result.found)
            with_award += int(result.adjudicaciones_upserted > 0)
            if index % 50 == 0 or index == len(codigos):
                print(
                    f"[{index}/{len(codigos)}] {codigo}: found={result.found} "
                    f"awards_upserted={result.adjudicaciones_upserted}"
                )
        except Exception as exc:  # noqa: BLE001 - one bad codigo must not abort the batch
            failed += 1
            print(f"[{index}/{len(codigos)}] {codigo}: FAILED ({exc})")
        await asyncio.sleep(_DELAY_SECONDS)

    with engine.connect() as connection:
        adjudicacion_rows = connection.scalar(text("SELECT count(*) FROM core.adjudicacion"))
        proveedor_rows = connection.scalar(text("SELECT count(*) FROM core.proveedor"))

    print(
        f"\nDone: {found} found, {failed} failed, {with_award} licitaciones with a real award loaded. "
        f"{adjudicacion_rows} rows in core.adjudicacion, {proveedor_rows} rows in core.proveedor."
    )


if __name__ == "__main__":
    asyncio.run(_run())
