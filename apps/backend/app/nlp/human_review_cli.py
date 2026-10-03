"""Human-in-the-Loop Review CLI (Fase 6.17) — queue inspection, interactive review,
reporting and feedback synchronization to the Gold Dataset.

Run as:
    python -m app.nlp.human_review_cli queue [--limit 20] [--threshold 0.65]
    python -m app.nlp.human_review_cli review --reviewer-email user@mercadoinsight.cl
    python -m app.nlp.human_review_cli sync-gold [--version 2026.2]
    python -m app.nlp.human_review_cli report
"""

from __future__ import annotations

import argparse
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.nlp.confidence import DEFAULT_LOW_CONFIDENCE_THRESHOLD
from app.nlp.human_review import ReviewDecision, validate_review_decision
from app.nlp.human_review_db import (
    ReviewQueueItem,
    fetch_review_history,
    fetch_review_queue,
    get_review_statistics,
    incorporate_feedback_to_gold_dataset,
    record_human_review,
)
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy
from app.nlp.taxonomy_db import resolve_category, resolve_subcategory


def _engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def _get_or_create_reviewer_id(connection: Connection, email: str) -> uuid.UUID:
    row = connection.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).first()
    if row is not None:
        return row[0]

    user_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at) "
            "VALUES (:id, :email, :hashed_password, true, now(), now())"
        ),
        {"id": user_id, "email": email, "hashed_password": get_password_hash("reviewer_password")},
    )
    connection.commit()
    return user_id


def _find_dataset_version_id(connection: Connection, version_str: str | None = None) -> uuid.UUID:
    if version_str:
        row = connection.execute(
            text("SELECT id FROM knowledge.dataset_versions WHERE version = :ver LIMIT 1"),
            {"ver": version_str},
        ).first()
        if row is None:
            raise SystemExit(f"No dataset_version found with version='{version_str}'")
        return row[0]

    row = connection.execute(
        text("SELECT id, version FROM knowledge.dataset_versions ORDER BY created_at DESC LIMIT 1")
    ).first()
    if row is None:
        raise SystemExit("No dataset_versions found. Run `python -m app.nlp.gold_dataset_cli sample` first.")
    return row[0]


def cmd_queue(args: argparse.Namespace) -> None:
    engine = _engine()
    with engine.connect() as conn:
        items = fetch_review_queue(
            conn,
            low_threshold=args.threshold,
            only_unreviewed=not args.all,
            limit=args.limit,
        )

        if not items:
            print("\nNo hay licitaciones pendientes en la cola de revisión humana.")
            return

        print(f"\n{'='*95}")
        print(f"COLA DE REVISIÓN HUMANA ({len(items)} items mostrados, threshold={args.threshold})")
        print(f"{'='*95}")
        print(f"{'Prioridad':<10} {'Código':<16} {'Conf':<6} {'Relev':<10} {'Cat. Predicha':<16} {'Motivos':<24} {'Título'}")
        print(f"{'-'*95}")

        for item in items:
            cat_str = item.category_code or "SIN CATEGORIA"
            reasons_str = ",".join(r.value for r in item.reasons)
            short_title = item.nombre[:40] + "..." if len(item.nombre) > 40 else item.nombre
            print(
                f"{item.priority:<10.2f} {item.codigo:<16} {item.confidence_score:<6.2f} "
                f"{item.relevance_tier or 'N/A':<10} {cat_str:<16} {reasons_str:<24} {short_title}"
            )
        print(f"{'='*95}\n")


def cmd_review(args: argparse.Namespace) -> None:
    engine = _engine()
    taxonomy: Taxonomy = load_initial_taxonomy()
    valid_categories = {c.code for c in taxonomy.categories}
    subcategories_by_category = {c.code: {s.code for s in c.subcategories} for c in taxonomy.categories}

    with engine.connect() as conn:
        reviewer_id = _get_or_create_reviewer_id(conn, args.reviewer_email)
        print(f"\nSesión de revisión iniciada para: {args.reviewer_email} (ID: {reviewer_id})")

        items = fetch_review_queue(
            conn,
            low_threshold=args.threshold,
            only_unreviewed=True,
            limit=args.limit,
        )

        if not items:
            print("No hay items pendientes en la cola de revisión.")
            return

        print(f"Se encontraron {len(items)} licitaciones para revisar. Comandos: [a]ceptar, [m]odificar, [s]altar, [q]uit.\n")

        reviewed_count = 0
        for idx, item in enumerate(items, start=1):
            print(f"{'='*80}")
            print(f"[{idx}/{len(items)}] Licitación: {item.codigo} — {item.nombre}")
            if item.organismo:
                print(f"Organismo: {item.organismo}")
            if item.monto_estimado:
                print(f"Monto Estimado: ${item.monto_estimado:,.0f}")
            if item.descripcion:
                desc = item.descripcion.strip()
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                print(f"Descripción: {desc}")
            if item.items:
                print(f"Ítems: {', '.join(item.items[:5])}")

            print(f"\n--- Predicción del Sistema ---")
            cat_display = item.category_code or "Sin Categoría"
            sub_display = item.subcategory_code or "Sin Subcategoría"
            print(f"Categoría: {cat_display} / {sub_display}")
            print(f"Confidence Score: {item.confidence_score:.3f} | Relevancia: {item.relevance_tier or 'N/A'}")
            print(f"Método ganador: {item.winning_method or 'N/A'}")
            if item.reasons:
                print(f"Motivos de revisión: {', '.join(r.value for r in item.reasons)}")
            if item.conflict_details:
                print(f"Detalle de conflicto: {item.conflict_details}")

            while True:
                choice = input("\nAcción ([a]ceptar / [m]odificar / [s]altar / [q]uit): ").strip().lower()
                if choice in ("a", "m", "s", "q"):
                    break
                print("Opción inválida.")

            if choice == "q":
                print("\nSesión finalizada por el usuario.")
                break
            if choice == "s":
                print("Saltado.")
                continue

            if choice == "a":
                # Accept current prediction
                is_relevant = item.category_id is not None or (item.relevance_tier and item.relevance_tier != "not_relevant")
                record_human_review(
                    conn,
                    classification_id=item.classification_id,
                    reviewer_id=reviewer_id,
                    accepted=True,
                    relevant=bool(is_relevant),
                    category_id=item.category_id,
                    subcategory_id=item.subcategory_id,
                    relevance_tier=item.relevance_tier,
                    reason="Predicción del clasificador aceptada por revisor.",
                )
                conn.commit()
                reviewed_count += 1
                print("✓ Clasificación aceptada y guardada.")

            elif choice == "m":
                # Modify prediction
                while True:
                    rel_input = input("¿Es relevante para el dominio (accesibilidad/ayudas técnicas/adultos mayores)? [s/n]: ").strip().lower()
                    if rel_input in ("s", "n"):
                        break

                is_relevant = rel_input == "s"
                new_cat_code: str | None = None
                new_sub_code: str | None = None
                new_tier: str | None = "not_relevant" if not is_relevant else "high"

                if is_relevant:
                    print("\nCategorías disponibles:")
                    cats_list = sorted(valid_categories)
                    for c_idx, c_code in enumerate(cats_list, 1):
                        print(f"  {c_idx}. {c_code}")
                    cat_num = input(f"Seleccione número de categoría [1-{len(cats_list)}]: ").strip()
                    try:
                        new_cat_code = cats_list[int(cat_num) - 1]
                    except (ValueError, IndexError):
                        print("Selección inválida, cancelando modificación.")
                        continue

                    # Subcategories
                    subs_list = sorted(subcategories_by_category.get(new_cat_code, set()))
                    if subs_list:
                        print(f"\nSubcategorías de '{new_cat_code}':")
                        for s_idx, s_code in enumerate(subs_list, 1):
                            print(f"  {s_idx}. {s_code}")
                        print(f"  0. Ninguna / No aplica")
                        sub_num = input(f"Seleccione número de subcategoría [0-{len(subs_list)}]: ").strip()
                        if sub_num != "0":
                            try:
                                new_sub_code = subs_list[int(sub_num) - 1]
                            except (ValueError, IndexError):
                                new_sub_code = None

                    tier_input = input("Relevance Tier [high/medium/low] (default: high): ").strip().lower()
                    new_tier = tier_input if tier_input in ("high", "medium", "low") else "high"

                reason = input("Motivo de la modificación: ").strip()
                decision = ReviewDecision(
                    accepted=False,
                    relevant=is_relevant,
                    category_code=new_cat_code,
                    subcategory_code=new_sub_code,
                    relevance_tier=new_tier,
                    reason=reason,
                )

                errors = validate_review_decision(
                    decision,
                    valid_categories=valid_categories,
                    subcategories_by_category=subcategories_by_category,
                )
                if errors:
                    print(f"Error de validación: {'; '.join(errors)}")
                    continue

                new_cat_id = resolve_category(conn, taxonomy, new_cat_code) if new_cat_code else None
                new_sub_id = (
                    resolve_subcategory(conn, taxonomy, new_cat_id, new_cat_code, new_sub_code)
                    if new_cat_code and new_sub_code and new_cat_id
                    else None
                )

                record_human_review(
                    conn,
                    classification_id=item.classification_id,
                    reviewer_id=reviewer_id,
                    accepted=False,
                    relevant=is_relevant,
                    category_id=new_cat_id,
                    subcategory_id=new_sub_id,
                    relevance_tier=new_tier,
                    reason=reason,
                )
                conn.commit()
                reviewed_count += 1
                print("✓ Modificación guardada correctamente.")

        print(f"\nResumen: {reviewed_count} licitaciones revisadas en esta sesión.")


def cmd_sync_gold(args: argparse.Namespace) -> None:
    engine = _engine()
    with engine.connect() as conn:
        dataset_ver_id = _find_dataset_version_id(conn, args.version)
        print(f"\nSincronizando revisiones humanas con Gold Dataset (ID: {dataset_ver_id})...")

        res = incorporate_feedback_to_gold_dataset(conn, dataset_version_id=dataset_ver_id)
        conn.commit()

        print(f"\n{'='*60}")
        print("FEEDBACK SINCRONIZADO CON EL GOLD DATASET")
        print(f"{'='*60}")
        print(f"Etiquetas nuevas insertadas: {res['inserted']}")
        print(f"Etiquetas existentes actualizadas: {res['updated']}")
        print(f"Total revisiones sincronizadas: {res['total_synced']}")
        print(f"Total registros en Gold Dataset: {res['record_count']}")
        print(f"{'='*60}\n")


def cmd_report(args: argparse.Namespace) -> None:
    engine = _engine()
    with engine.connect() as conn:
        stats = get_review_statistics(conn)
        history = fetch_review_history(conn, limit=args.limit)

        print(f"\n{'='*75}")
        print("REPORTE DE REVISIÓN HUMANA (HUMAN-IN-THE-LOOP)")
        print(f"{'='*75}")
        print(f"Total Revisiones Completadas: {stats['total_reviews']}")
        print(f"  - Aceptadas: {stats['accepted_count']} ({stats['acceptance_rate']*100:.1f}%)")
        print(f"  - Modificadas: {stats['modified_count']}")
        print(f"Licitaciones pendientes en cola: {stats['unreviewed_classifications']}")
        print(f"{'-'*75}")

        if history:
            print("\nÚltimas revisiones registradas:")
            for h in history[:10]:
                status_str = "ACEPTADA" if h["accepted"] else "MODIFICADA"
                cat_str = f"{h['category_code'] or 'none'}/{h['subcategory_code'] or 'none'}"
                reason_str = f" — Motivo: {h['reason']}" if h.get("reason") else ""
                print(f"  [{status_str}] {h['codigo']} (rev por {h['reviewer_email']}): {cat_str}{reason_str}")
        else:
            print("Aún no hay revisiones registradas en la base de datos.")

        print(f"{'='*75}\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.nlp.human_review_cli", description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # queue
    p_queue = subparsers.add_parser("queue", help="Muestra la cola de predicciones de baja confianza")
    p_queue.add_argument("--limit", type=int, default=20, help="Cantidad máxima de items a mostrar")
    p_queue.add_argument("--threshold", type=float, default=DEFAULT_LOW_CONFIDENCE_THRESHOLD, help="Umbral de baja confianza")
    p_queue.add_argument("--all", action="store_true", help="Incluye clasificaciones ya revisadas")
    p_queue.set_defaults(func=cmd_queue)

    # review
    p_review = subparsers.add_parser("review", help="Inicia sesión interactiva de revisión humana")
    p_review.add_argument("--reviewer-email", default="revisor@mercadoinsight.cl", help="Email del revisor humano")
    p_review.add_argument("--limit", type=int, default=20, help="Cantidad máxima de licitaciones a revisar")
    p_review.add_argument("--threshold", type=float, default=DEFAULT_LOW_CONFIDENCE_THRESHOLD, help="Umbral de baja confianza")
    p_review.set_defaults(func=cmd_review)

    # sync-gold
    p_sync = subparsers.add_parser("sync-gold", help="Sincroniza feedback humano con el Gold Dataset")
    p_sync.add_argument("--version", help="Versión del Gold Dataset (ej. 2026.2)")
    p_sync.set_defaults(func=cmd_sync_gold)

    # report
    p_report = subparsers.add_parser("report", help="Muestra métricas y estadísticas de revisiones")
    p_report.add_argument("--limit", type=int, default=20, help="Cantidad de revisiones recientes a mostrar")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
