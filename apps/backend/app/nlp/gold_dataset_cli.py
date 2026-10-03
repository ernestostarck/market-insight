"""Gold Dataset CLI (Fase 6.13) — sampling, human labeling, splitting,
reporting and finalizing the labeled dataset 6.14 needs to train/evaluate
against. Run as ``python -m app.nlp.gold_dataset_cli <subcommand>``.

``label`` is the one subcommand meant to be run interactively by a human
in their own terminal — it is the actual ground-truth-producing step and
cannot be scripted or faked (see docs/07-ai/gold-dataset.md).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.nlp.gold_dataset import (
    assign_splits, compute_class_distribution, detect_imbalance, detect_inconsistencies, select_sample,
)
from app.nlp.gold_dataset_db import (
    count_pending_labels, create_dataset_version, fetch_labeled_rows, fetch_pending_labels,
    finalize_dataset_version, insert_pending_labels, save_label, save_splits,
)
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy

_DATASET_NAME = "gold-dataset"


def _engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def _latest_dataset_version_id(connection: Connection) -> uuid.UUID:
    row = connection.execute(
        text(
            "SELECT id FROM knowledge.dataset_versions WHERE name = :name ORDER BY created_at DESC LIMIT 1"
        ),
        {"name": _DATASET_NAME},
    ).first()
    if row is None:
        raise SystemExit("no dataset_versions row found yet — run `sample` first")
    return row[0]


def _fetch_all_licitacion_ids(connection: Connection) -> list[int]:
    return [row[0] for row in connection.execute(text("SELECT id FROM core.licitacion")).all()]


def _fetch_keyword_candidate_ids(connection: Connection, terms: list[str]) -> list[int]:
    patterns = [f"%{term}%" for term in terms]
    rows = connection.execute(
        text(
            "SELECT DISTINCT id FROM core.licitacion "
            "WHERE nombre ILIKE ANY(:patterns) OR descripcion ILIKE ANY(:patterns)"
        ),
        {"patterns": patterns},
    ).all()
    return [row[0] for row in rows]


def _fetch_codigos(connection: Connection, licitacion_ids: tuple[int, ...]) -> dict[int, str]:
    if not licitacion_ids:
        return {}
    rows = connection.execute(
        text("SELECT id, codigo FROM core.licitacion WHERE id = ANY(:ids)"),
        {"ids": list(licitacion_ids)},
    ).all()
    return {row.id: row.codigo for row in rows}


def _enrich_all(codigos: list[str]) -> None:
    from app.etl.enrichment import enrich_licitacion_detail as _enrich
    from app.etl.loading.core_schema import CoreLicitacionItemLoader, CoreLicitacionLoader
    from app.integrations.chilecompra.config import ChileCompraConfig
    from app.integrations.chilecompra.sdk import ChileCompraClient as ChileCompraSDK

    engine = _engine()
    client = ChileCompraSDK.from_config(ChileCompraConfig.from_settings())
    licitacion_loader = CoreLicitacionLoader(lambda: engine.connect())
    item_loader = CoreLicitacionItemLoader(lambda: engine.connect())

    async def _run() -> None:
        for codigo in codigos:
            result = await _enrich(
                codigo, client=client, licitacion_loader=licitacion_loader,
                item_loader=item_loader, connection_factory=lambda: engine.connect(),
            )
            print(f"  enriched {codigo}: found={result.found} items_upserted={result.items_upserted}")

    asyncio.run(_run())


def cmd_sample(args: argparse.Namespace) -> None:
    dictionary = load_initial_dictionary()
    taxonomy = load_initial_taxonomy()
    terms = sorted({form.strip() for entry in dictionary.entries for form in entry.all_surface_forms() if form.strip()})

    engine = _engine()
    connection = engine.connect()
    try:
        all_ids = _fetch_all_licitacion_ids(connection)
        if not all_ids:
            raise SystemExit("core.licitacion is empty — run a real ETL ingest first (see docs/07-ai/gold-dataset.md)")
        keyword_ids = _fetch_keyword_candidate_ids(connection, terms)
        sampled_ids = select_sample(
            all_ids, keyword_ids, target_size=args.size, keyword_share=args.keyword_share, seed=args.seed,
        )
        codigos_by_id = _fetch_codigos(connection, sampled_ids)

        manifest = {
            "status": "pending_labels",
            "sample_size": len(sampled_ids),
            "keyword_share": args.keyword_share,
            "seed": args.seed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        dataset_version_id = create_dataset_version(
            connection, name=_DATASET_NAME, version=args.version,
            taxonomy_version=taxonomy.version, manifest=manifest,
        )
        insert_pending_labels(connection, dataset_version_id, list(sampled_ids))
        connection.commit()
        print(f"created dataset_version {dataset_version_id} ({args.version}), {len(sampled_ids)} pending labels")
    finally:
        connection.close()

    print(f"enriching {len(codigos_by_id)} licitaciones (real ChileCompra API calls)...")
    _enrich_all([codigo for codigo in codigos_by_id.values() if codigo])
    print("done. Run `label --labeled-by <tu email>` to start etiquetando.")


def cmd_label(args: argparse.Namespace) -> None:
    taxonomy = load_initial_taxonomy()
    engine = _engine()
    connection = engine.connect()
    try:
        dataset_version_id = _latest_dataset_version_id(connection)
        pending = fetch_pending_labels(connection, dataset_version_id)
        if not pending:
            print("no pending labels — everything in the active dataset_version is already labeled.")
            return

        for index, item in enumerate(pending, start=1):
            print(f"\n[{index}/{len(pending)}] {item['codigo']} — {item['nombre']}")
            if item["organismo"]:
                print(f"  organismo: {item['organismo']}")
            if item["monto_estimado"] is not None:
                print(f"  monto estimado: {item['monto_estimado']}")
            if item["descripcion"]:
                print(f"  descripcion: {item['descripcion']}")
            if item["items"]:
                print(f"  items: {', '.join(item['items'])}")

            relevant = _prompt_yes_no("  ¿relevante para el dominio (accesibilidad/ayudas técnicas/adultos mayores)? (s/n/q)")
            if relevant is None:
                print("saliendo — el resto queda pendiente para la próxima corrida.")
                return

            category_id = subcategory_id = None
            if relevant:
                category_id, category_code = _prompt_category(connection, taxonomy)
                subcategory_id = _prompt_subcategory(connection, taxonomy, category_code, category_id)
            notes = input("  notas (opcional): ").strip() or None

            save_label(
                connection, dataset_version_id, item["licitacion_id"], relevant=relevant,
                category_id=category_id, subcategory_id=subcategory_id,
                taxonomy_version=taxonomy.version, labeled_by=args.labeled_by, notes=notes,
            )
            connection.commit()
        print("\nmuestra completa etiquetada. Corre `split` y luego `report`.")
    finally:
        connection.close()


def _prompt_yes_no(prompt: str) -> bool | None:
    while True:
        answer = input(f"{prompt} ").strip().lower()
        if answer in ("s", "si", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        if answer == "q":
            return None
        print("  respuesta invalida, usa s/n/q")


def _prompt_category(connection: Connection, taxonomy: Taxonomy) -> tuple[int, str]:
    from app.nlp.taxonomy_db import resolve_category

    while True:
        for index, category in enumerate(taxonomy.categories, start=1):
            print(f"    {index}. {category.code} — {category.name}")
        choice = input("  categoria (numero): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(taxonomy.categories):
            category = taxonomy.categories[int(choice) - 1]
            return resolve_category(connection, taxonomy, category.code), category.code
        print("  opcion invalida")


def _prompt_subcategory(connection: Connection, taxonomy: Taxonomy, category_code: str, category_id: int) -> int | None:
    from app.nlp.taxonomy_db import resolve_subcategory

    category = taxonomy.category(category_code)
    if not category.subcategories:
        return None
    while True:
        for index, subcategory in enumerate(category.subcategories, start=1):
            print(f"    {index}. {subcategory.code} — {subcategory.name}")
        choice = input("  subcategoria (numero, enter para omitir): ").strip()
        if choice == "":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(category.subcategories):
            subcategory = category.subcategories[int(choice) - 1]
            return resolve_subcategory(connection, taxonomy, category_id, category_code, subcategory.code)
        print("  opcion invalida")


def cmd_split(args: argparse.Namespace) -> None:
    engine = _engine()
    connection = engine.connect()
    try:
        dataset_version_id = _latest_dataset_version_id(connection)
        labeled = fetch_labeled_rows(connection, dataset_version_id)
        if not labeled:
            raise SystemExit("no hay filas etiquetadas todavia — corre `label` primero")

        grouped: dict[str, list[int]] = {}
        for row in labeled:
            key = row["category_code"] if row["relevant"] else "not_relevant"
            grouped.setdefault(key, []).append(row["licitacion_id"])

        assignment = assign_splits(grouped, seed=args.seed)
        save_splits(connection, dataset_version_id, assignment)
        connection.commit()
        print(f"split asignado a {len(assignment)} filas etiquetadas.")
    finally:
        connection.close()


def cmd_report(args: argparse.Namespace) -> None:
    engine = _engine()
    connection = engine.connect()
    try:
        dataset_version_id = _latest_dataset_version_id(connection)
        labeled = fetch_labeled_rows(connection, dataset_version_id)
        pending_count = count_pending_labels(connection, dataset_version_id)
    finally:
        connection.close()

    print(f"dataset_version: {dataset_version_id}")
    print(f"etiquetadas: {len(labeled)} | pendientes: {pending_count}")

    distribution = compute_class_distribution(labeled)
    print("\ndistribucion de clases:")
    for code, count in sorted(distribution.counts.items()):
        print(f"  {code}: {count} ({distribution.share(code):.1%})")

    imbalanced = detect_imbalance(distribution)
    if imbalanced:
        print(f"\nclases desbalanceadas (< 10% del total): {', '.join(imbalanced)}")

    inconsistencies = detect_inconsistencies(labeled)
    if inconsistencies:
        print("\ninconsistencias encontradas:")
        for issue in inconsistencies:
            print(f"  - {issue}")
    else:
        print("\nsin inconsistencias.")

    split_counts: dict[str, int] = {}
    for row in labeled:
        split_counts[row["split"] or "sin_split"] = split_counts.get(row["split"] or "sin_split", 0) + 1
    print("\nsplits:")
    for split, count in sorted(split_counts.items()):
        print(f"  {split}: {count}")


def cmd_finalize(args: argparse.Namespace) -> None:
    engine = _engine()
    connection = engine.connect()
    try:
        dataset_version_id = _latest_dataset_version_id(connection)
        pending_count = count_pending_labels(connection, dataset_version_id)
        if pending_count:
            raise SystemExit(f"quedan {pending_count} filas sin etiquetar — corre `label` hasta terminar")

        labeled = fetch_labeled_rows(connection, dataset_version_id)
        if any(row["split"] is None for row in labeled):
            raise SystemExit("hay filas etiquetadas sin split — corre `split` primero")

        distribution = compute_class_distribution(labeled)
        labeled_by_counts: dict[str, int] = {}
        for row in labeled:
            labeled_by_counts[row["labeled_by"]] = labeled_by_counts.get(row["labeled_by"], 0) + 1
        manifest = {
            "status": "ready",
            "finalized_at": datetime.now(timezone.utc).isoformat(),
            "class_distribution": distribution.counts,
            "imbalanced_classes": list(detect_imbalance(distribution)),
            "split_counts": {
                split: sum(1 for row in labeled if row["split"] == split)
                for split in ("train", "validation", "test")
            },
            "labeled_by_counts": labeled_by_counts,
        }
        finalize_dataset_version(connection, dataset_version_id, record_count=len(labeled), manifest=manifest)
        connection.commit()
        print(f"dataset_version {dataset_version_id} finalizado con {len(labeled)} registros.")
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Gold Dataset CLI (Fase 6.13)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample_parser = subparsers.add_parser("sample", help="select and enrich a stratified sample")
    sample_parser.add_argument("--size", type=int, default=40)
    sample_parser.add_argument("--keyword-share", type=float, default=0.5)
    sample_parser.add_argument("--seed", type=int, default=42)
    sample_parser.add_argument("--version", default="2026.1")
    sample_parser.set_defaults(func=cmd_sample)

    label_parser = subparsers.add_parser("label", help="interactively label the pending sample")
    label_parser.add_argument("--labeled-by", required=True)
    label_parser.set_defaults(func=cmd_label)

    split_parser = subparsers.add_parser("split", help="assign train/validation/test to labeled rows")
    split_parser.add_argument("--seed", type=int, default=42)
    split_parser.set_defaults(func=cmd_split)

    report_parser = subparsers.add_parser("report", help="print class distribution, imbalance and inconsistencies")
    report_parser.set_defaults(func=cmd_report)

    finalize_parser = subparsers.add_parser("finalize", help="close out the current dataset_version")
    finalize_parser.set_defaults(func=cmd_finalize)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
