"""Core (Connection + text()) persistence for the Gold Dataset (6.13/6.14).

Same style as app/nlp/taxonomy_db.py / product_taxonomy_db.py: plain
functions over a Connection, no ORM session — this is meant to be called
both from the CLI (app/nlp/gold_dataset_cli.py) and from scratch
verification scripts, same as every other NLP stage in this codebase.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.preprocessing import TextPreprocessor


def create_dataset_version(
    connection: Connection, *, name: str, version: str, taxonomy_version: str, manifest: dict,
) -> uuid.UUID:
    dataset_version_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO knowledge.dataset_versions (id, name, version, taxonomy_version, record_count, manifest) "
            "VALUES (:id, :name, :version, :taxonomy_version, :record_count, :manifest)"
        ),
        {
            "id": dataset_version_id, "name": name, "version": version, "taxonomy_version": taxonomy_version,
            "record_count": 0, "manifest": json.dumps(manifest),
        },
    )
    return dataset_version_id


def insert_pending_labels(connection: Connection, dataset_version_id: uuid.UUID, licitacion_ids: list[int]) -> None:
    for licitacion_id in licitacion_ids:
        connection.execute(
            text(
                "INSERT INTO knowledge.gold_labels (id, dataset_version_id, licitacion_id) "
                "VALUES (:id, :dataset_version_id, :licitacion_id)"
            ),
            {"id": uuid.uuid4(), "dataset_version_id": dataset_version_id, "licitacion_id": licitacion_id},
        )


def fetch_pending_labels(connection: Connection, dataset_version_id: uuid.UUID) -> list[dict]:
    rows = connection.execute(
        text(
            "SELECT gl.licitacion_id, l.codigo, l.nombre, l.descripcion, l.monto_estimado, o.nombre AS organismo "
            "FROM knowledge.gold_labels gl "
            "JOIN core.licitacion l ON l.id = gl.licitacion_id "
            "LEFT JOIN core.organismo o ON o.id = l.organismo_id "
            "WHERE gl.dataset_version_id = :dataset_version_id AND gl.relevant IS NULL "
            "ORDER BY gl.licitacion_id"
        ),
        {"dataset_version_id": dataset_version_id},
    ).all()
    pending = []
    for row in rows:
        items = connection.execute(
            text("SELECT nombre FROM core.licitacion_item WHERE licitacion_id = :licitacion_id"),
            {"licitacion_id": row.licitacion_id},
        ).all()
        pending.append({
            "licitacion_id": row.licitacion_id, "codigo": row.codigo, "nombre": row.nombre,
            "descripcion": row.descripcion, "monto_estimado": row.monto_estimado, "organismo": row.organismo,
            "items": [item[0] for item in items],
        })
    return pending


def save_label(
    connection: Connection,
    dataset_version_id: uuid.UUID,
    licitacion_id: int,
    *,
    relevant: bool,
    category_id: int | None,
    subcategory_id: int | None,
    taxonomy_version: str,
    labeled_by: str,
    notes: str | None,
) -> None:
    connection.execute(
        text(
            "UPDATE knowledge.gold_labels SET "
            "relevant = :relevant, category_id = :category_id, subcategory_id = :subcategory_id, "
            "taxonomy_version = :taxonomy_version, labeled_by = :labeled_by, labeled_at = :labeled_at, "
            "notes = :notes, updated_at = now() "
            "WHERE dataset_version_id = :dataset_version_id AND licitacion_id = :licitacion_id"
        ),
        {
            "relevant": relevant, "category_id": category_id, "subcategory_id": subcategory_id,
            "taxonomy_version": taxonomy_version, "labeled_by": labeled_by,
            "labeled_at": datetime.now(timezone.utc), "notes": notes,
            "dataset_version_id": dataset_version_id, "licitacion_id": licitacion_id,
        },
    )


def fetch_labeled_rows(connection: Connection, dataset_version_id: uuid.UUID) -> list[dict]:
    rows = connection.execute(
        text(
            "SELECT gl.licitacion_id, gl.relevant, gl.category_id, c.code AS category_code, "
            "gl.subcategory_id, sc.category_id AS subcategory_category_id, gl.split, gl.labeled_by "
            "FROM knowledge.gold_labels gl "
            "LEFT JOIN knowledge.categories c ON c.id = gl.category_id "
            "LEFT JOIN knowledge.subcategories sc ON sc.id = gl.subcategory_id "
            "WHERE gl.dataset_version_id = :dataset_version_id AND gl.relevant IS NOT NULL "
            "ORDER BY gl.licitacion_id"
        ),
        {"dataset_version_id": dataset_version_id},
    ).all()
    return [
        {
            "licitacion_id": row.licitacion_id, "relevant": row.relevant, "category_id": row.category_id,
            "category_code": row.category_code, "subcategory_id": row.subcategory_id,
            "subcategory_category_id": row.subcategory_category_id, "split": row.split,
            "labeled_by": row.labeled_by,
        }
        for row in rows
    ]


def count_pending_labels(connection: Connection, dataset_version_id: uuid.UUID) -> int:
    row = connection.execute(
        text(
            "SELECT count(*) FROM knowledge.gold_labels "
            "WHERE dataset_version_id = :dataset_version_id AND relevant IS NULL"
        ),
        {"dataset_version_id": dataset_version_id},
    ).first()
    return int(row[0])


def save_splits(connection: Connection, dataset_version_id: uuid.UUID, assignment: dict[int, str]) -> None:
    for licitacion_id, split in assignment.items():
        connection.execute(
            text(
                "UPDATE knowledge.gold_labels SET split = :split, updated_at = now() "
                "WHERE dataset_version_id = :dataset_version_id AND licitacion_id = :licitacion_id"
            ),
            {"split": split, "dataset_version_id": dataset_version_id, "licitacion_id": licitacion_id},
        )


def finalize_dataset_version(
    connection: Connection, dataset_version_id: uuid.UUID, *, record_count: int, manifest: dict,
) -> None:
    connection.execute(
        text(
            "UPDATE knowledge.dataset_versions SET record_count = :record_count, manifest = :manifest, "
            "updated_at = now() WHERE id = :id"
        ),
        {"record_count": record_count, "manifest": json.dumps(manifest), "id": dataset_version_id},
    )


def ensure_documents(connection: Connection, licitacion_ids: list[int]) -> None:
    """Gold-labeled licitaciones never went through the sync NLP path
    (`sample`/`label` only touch core.licitacion/licitacion_item) — 6.14
    needs `knowledge.documents.normalized_text` to train on, built the
    same way 6.1/6.2 build it (`TextPreprocessor.build_tender_document`)
    so the same content_hash is reusable if these licitaciones later go
    through the real async pipeline."""
    preprocessor = TextPreprocessor()
    for licitacion_id in licitacion_ids:
        existing = connection.execute(
            text("SELECT 1 FROM knowledge.documents WHERE licitacion_id = :licitacion_id LIMIT 1"),
            {"licitacion_id": licitacion_id},
        ).first()
        if existing is not None:
            continue

        licitacion = connection.execute(
            text("SELECT nombre, descripcion FROM core.licitacion WHERE id = :licitacion_id"),
            {"licitacion_id": licitacion_id},
        ).first()
        if licitacion is None:
            continue

        items = connection.execute(
            text("SELECT nombre FROM core.licitacion_item WHERE licitacion_id = :licitacion_id"),
            {"licitacion_id": licitacion_id},
        ).all()
        preprocessed = preprocessor.build_tender_document(
            title=licitacion.nombre, description=licitacion.descripcion,
            item_texts=[item[0] for item in items],
        )
        content_hash = hashlib.sha256(preprocessed.normalized_text.encode("utf-8")).hexdigest()
        connection.execute(
            text(
                "INSERT INTO knowledge.documents (id, licitacion_id, raw_text, normalized_text, language, content_hash) "
                "VALUES (:id, :licitacion_id, :raw_text, :normalized_text, :language, :content_hash)"
            ),
            {
                "id": uuid.uuid4(), "licitacion_id": licitacion_id, "raw_text": preprocessed.original_text,
                "normalized_text": preprocessed.normalized_text, "language": preprocessed.language,
                "content_hash": content_hash,
            },
        )


def fetch_training_rows(connection: Connection, dataset_version_id: uuid.UUID) -> list[dict]:
    """One row per labeled licitación: `label` is the category code, or
    "not_relevant" — same convention as `compute_class_distribution`
    (app/nlp/gold_dataset.py). Requires `ensure_documents` to have run
    first for this dataset_version's licitaciones."""
    rows = connection.execute(
        text(
            "SELECT DISTINCT ON (gl.licitacion_id) gl.licitacion_id, gl.relevant, c.code AS category_code, "
            "gl.split, d.normalized_text "
            "FROM knowledge.gold_labels gl "
            "LEFT JOIN knowledge.categories c ON c.id = gl.category_id "
            "JOIN knowledge.documents d ON d.licitacion_id = gl.licitacion_id "
            "WHERE gl.dataset_version_id = :dataset_version_id AND gl.relevant IS NOT NULL "
            "ORDER BY gl.licitacion_id, d.created_at DESC"
        ),
        {"dataset_version_id": dataset_version_id},
    ).all()
    return [
        {
            "licitacion_id": row.licitacion_id,
            "label": row.category_code if row.relevant else "not_relevant",
            "split": row.split,
            "text": row.normalized_text,
        }
        for row in rows
    ]
