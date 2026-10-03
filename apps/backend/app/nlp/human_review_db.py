"""Database persistence and queries for Human-in-the-Loop review & Gold Dataset feedback (Fase 6.17).

Provides functions over an SQLAlchemy Connection (connection + text(), no ORM session,
matching app/nlp/gold_dataset_db.py) to:
1. Fetch and prioritize the low-confidence review queue.
2. Record human review decisions (accept or modify category, subcategory, relevance).
3. Query review history and statistics.
4. Incorporate reviewed feedback into the Gold Dataset for model retraining.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.confidence import (
    DEFAULT_CONFLICT_MARGIN,
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    ReviewReason,
    evaluate_prediction_confidence,
)
from app.nlp.gold_dataset_db import ensure_documents
from app.nlp.human_review import compute_review_priority


@dataclass(frozen=True, slots=True)
class ReviewQueueItem:
    classification_id: uuid.UUID
    licitacion_id: int
    codigo: str
    nombre: str
    descripcion: str | None
    monto_estimado: float | None
    organismo: str | None
    items: tuple[str, ...]
    category_id: int | None
    category_code: str | None
    subcategory_id: int | None
    subcategory_code: str | None
    confidence_score: float
    rule_score: float | None
    similarity_score: float | None
    model_score: float | None
    relevance_score: float | None
    relevance_tier: str | None
    winning_method: str | None
    explanation: dict
    reasons: tuple[ReviewReason, ...]
    conflict_details: str | None
    priority: float


def fetch_review_queue(
    connection: Connection,
    *,
    low_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    conflict_margin: float = DEFAULT_CONFLICT_MARGIN,
    only_unreviewed: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[ReviewQueueItem]:
    """Retrieves candidates for human review, evaluated and ranked by uncertainty & relevance."""
    base_query = (
        "SELECT c.id AS classification_id, c.licitacion_id, c.category_id, cat.code AS category_code, "
        "c.subcategory_id, sub.code AS subcategory_code, c.confidence_score, c.rule_score, "
        "c.similarity_score, c.model_score, c.relevance_score, c.relevance_tier, c.explanation, "
        "l.codigo, l.nombre, l.descripcion, l.monto_estimado, o.nombre AS organismo "
        "FROM knowledge.classifications c "
        "JOIN core.licitacion l ON l.id = c.licitacion_id "
        "LEFT JOIN core.organismo o ON o.id = l.organismo_id "
        "LEFT JOIN knowledge.categories cat ON cat.id = c.category_id "
        "LEFT JOIN knowledge.subcategories sub ON sub.id = c.subcategory_id "
    )
    if only_unreviewed:
        base_query += (
            "LEFT JOIN knowledge.human_reviews hr ON hr.classification_id = c.id "
            "WHERE hr.id IS NULL "
        )

    rows = connection.execute(text(base_query)).all()

    candidates: list[ReviewQueueItem] = []
    for row in rows:
        expl = row.explanation if isinstance(row.explanation, dict) else {}
        if isinstance(row.explanation, str):
            try:
                expl = json.loads(row.explanation)
            except Exception:
                expl = {}

        hybrid_info = expl.get("hybrid", {})
        scores = hybrid_info.get("scores")
        categories = hybrid_info.get("categories")
        winning_method = hybrid_info.get("winning_method")

        assessment = evaluate_prediction_confidence(
            row.confidence_score,
            scores=scores,
            categories=categories,
            category_code=row.category_code,
            relevance_tier=row.relevance_tier,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
            conflict_margin=conflict_margin,
        )

        if assessment.needs_review:
            priority = compute_review_priority(
                row.relevance_tier,
                row.relevance_score,
                row.confidence_score,
                assessment.reasons,
            )
            candidates.append(
                ReviewQueueItem(
                    classification_id=row.classification_id,
                    licitacion_id=row.licitacion_id,
                    codigo=row.codigo,
                    nombre=row.nombre,
                    descripcion=row.descripcion,
                    monto_estimado=float(row.monto_estimado) if row.monto_estimado is not None else None,
                    organismo=row.organismo,
                    items=(),  # Populated below for the paginated slice
                    category_id=row.category_id,
                    category_code=row.category_code,
                    subcategory_id=row.subcategory_id,
                    subcategory_code=row.subcategory_code,
                    confidence_score=float(row.confidence_score),
                    rule_score=float(row.rule_score) if row.rule_score is not None else None,
                    similarity_score=float(row.similarity_score) if row.similarity_score is not None else None,
                    model_score=float(row.model_score) if row.model_score is not None else None,
                    relevance_score=float(row.relevance_score) if row.relevance_score is not None else None,
                    relevance_tier=row.relevance_tier,
                    winning_method=winning_method,
                    explanation=expl,
                    reasons=assessment.reasons,
                    conflict_details=assessment.conflict_details,
                    priority=priority,
                )
            )

    # Sort descending by priority, then ascending by confidence_score
    candidates.sort(key=lambda item: (-item.priority, item.confidence_score))

    # Paginate
    slice_items = candidates[offset : offset + limit]

    # Populate item names for the paginated slice
    result: list[ReviewQueueItem] = []
    for candidate in slice_items:
        item_rows = connection.execute(
            text("SELECT nombre FROM core.licitacion_item WHERE licitacion_id = :licitacion_id"),
            {"licitacion_id": candidate.licitacion_id},
        ).all()
        item_names = tuple(row[0] for row in item_rows if row[0])
        result.append(
            ReviewQueueItem(
                classification_id=candidate.classification_id,
                licitacion_id=candidate.licitacion_id,
                codigo=candidate.codigo,
                nombre=candidate.nombre,
                descripcion=candidate.descripcion,
                monto_estimado=candidate.monto_estimado,
                organismo=candidate.organismo,
                items=item_names,
                category_id=candidate.category_id,
                category_code=candidate.category_code,
                subcategory_id=candidate.subcategory_id,
                subcategory_code=candidate.subcategory_code,
                confidence_score=candidate.confidence_score,
                rule_score=candidate.rule_score,
                similarity_score=candidate.similarity_score,
                model_score=candidate.model_score,
                relevance_score=candidate.relevance_score,
                relevance_tier=candidate.relevance_tier,
                winning_method=candidate.winning_method,
                explanation=candidate.explanation,
                reasons=candidate.reasons,
                conflict_details=candidate.conflict_details,
                priority=candidate.priority,
            )
        )

    return result


def record_human_review(
    connection: Connection,
    *,
    classification_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    accepted: bool,
    relevant: bool,
    category_id: int | None = None,
    subcategory_id: int | None = None,
    relevance_tier: str | None = None,
    reason: str | None = None,
) -> uuid.UUID:
    """Persists a human review decision into knowledge.human_reviews and updates knowledge.classifications."""
    # Check if review already exists for this (classification, reviewer) pair
    existing = connection.execute(
        text(
            "SELECT id FROM knowledge.human_reviews "
            "WHERE classification_id = :classification_id AND reviewer_id = :reviewer_id"
        ),
        {"classification_id": classification_id, "reviewer_id": reviewer_id},
    ).first()

    review_id = existing[0] if existing else uuid.uuid4()
    now_dt = datetime.now(timezone.utc)

    if existing:
        connection.execute(
            text(
                "UPDATE knowledge.human_reviews SET "
                "accepted = :accepted, relevant = :relevant, category_id = :category_id, "
                "subcategory_id = :subcategory_id, relevance_tier = :relevance_tier, "
                "reason = :reason, updated_at = :updated_at "
                "WHERE id = :id"
            ),
            {
                "accepted": accepted,
                "relevant": relevant,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "relevance_tier": relevance_tier,
                "reason": reason,
                "updated_at": now_dt,
                "id": review_id,
            },
        )
    else:
        connection.execute(
            text(
                "INSERT INTO knowledge.human_reviews "
                "(id, classification_id, reviewer_id, accepted, relevant, category_id, subcategory_id, relevance_tier, reason, created_at, updated_at) "
                "VALUES (:id, :classification_id, :reviewer_id, :accepted, :relevant, :category_id, :subcategory_id, :relevance_tier, :reason, :created_at, :updated_at)"
            ),
            {
                "id": review_id,
                "classification_id": classification_id,
                "reviewer_id": reviewer_id,
                "accepted": accepted,
                "relevant": relevant,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "relevance_tier": relevance_tier,
                "reason": reason,
                "created_at": now_dt,
                "updated_at": now_dt,
            },
        )

    # Fetch current classification to merge explanation and update prediction
    cl_row = connection.execute(
        text("SELECT category_id, subcategory_id, explanation, relevance_score FROM knowledge.classifications WHERE id = :id"),
        {"id": classification_id},
    ).first()

    if cl_row:
        expl = cl_row.explanation if isinstance(cl_row.explanation, dict) else {}
        if isinstance(cl_row.explanation, str):
            try:
                expl = json.loads(cl_row.explanation)
            except Exception:
                expl = {}

        expl["human_review"] = {
            "review_id": str(review_id),
            "reviewed_by": str(reviewer_id),
            "accepted": accepted,
            "relevant": relevant,
            "reviewed_at": now_dt.isoformat(),
            "reason": reason,
        }

        # Human ground truth sets confidence_score = 1.0
        final_category_id = category_id if not accepted else cl_row.category_id
        final_subcategory_id = subcategory_id if not accepted else cl_row.subcategory_id
        final_relevance_tier = relevance_tier

        connection.execute(
            text(
                "UPDATE knowledge.classifications SET "
                "category_id = :category_id, subcategory_id = :subcategory_id, "
                "confidence_score = 1.0, relevance_tier = :relevance_tier, "
                "explanation = :explanation, updated_at = :updated_at "
                "WHERE id = :id"
            ),
            {
                "category_id": final_category_id,
                "subcategory_id": final_subcategory_id,
                "relevance_tier": final_relevance_tier,
                "explanation": json.dumps(expl),
                "updated_at": now_dt,
                "id": classification_id,
            },
        )

    return review_id


def fetch_review_history(connection: Connection, *, limit: int = 50, offset: int = 0) -> list[dict]:
    """Queries completed human reviews with user and tender metadata."""
    rows = connection.execute(
        text(
            "SELECT hr.id, hr.classification_id, hr.reviewer_id, u.email AS reviewer_email, "
            "hr.accepted, hr.relevant, hr.category_id, c.code AS category_code, "
            "hr.subcategory_id, sc.code AS subcategory_code, hr.relevance_tier, hr.reason, "
            "hr.created_at, l.id AS licitacion_id, l.codigo, l.nombre "
            "FROM knowledge.human_reviews hr "
            "JOIN knowledge.classifications cl ON cl.id = hr.classification_id "
            "JOIN core.licitacion l ON l.id = cl.licitacion_id "
            "JOIN users u ON u.id = hr.reviewer_id "
            "LEFT JOIN knowledge.categories c ON c.id = hr.category_id "
            "LEFT JOIN knowledge.subcategories sc ON sc.id = hr.subcategory_id "
            "ORDER BY hr.created_at DESC "
            "LIMIT :limit OFFSET :offset"
        ),
        {"limit": limit, "offset": offset},
    ).all()

    return [
        {
            "id": row.id,
            "classification_id": row.classification_id,
            "reviewer_id": row.reviewer_id,
            "reviewer_email": row.reviewer_email,
            "accepted": row.accepted,
            "relevant": row.relevant,
            "category_id": row.category_id,
            "category_code": row.category_code,
            "subcategory_id": row.subcategory_id,
            "subcategory_code": row.subcategory_code,
            "relevance_tier": row.relevance_tier,
            "reason": row.reason,
            "created_at": row.created_at,
            "licitacion_id": row.licitacion_id,
            "codigo": row.codigo,
            "nombre": row.nombre,
        }
        for row in rows
    ]


def get_review_statistics(connection: Connection) -> dict:
    """Computes overall statistics on human review queue and decisions."""
    total_reviews = int(connection.execute(text("SELECT count(*) FROM knowledge.human_reviews")).scalar() or 0)
    accepted_count = int(
        connection.execute(text("SELECT count(*) FROM knowledge.human_reviews WHERE accepted = true")).scalar() or 0
    )
    modified_count = int(
        connection.execute(text("SELECT count(*) FROM knowledge.human_reviews WHERE accepted = false")).scalar() or 0
    )

    unreviewed_classifications = int(
        connection.execute(
            text(
                "SELECT count(*) FROM knowledge.classifications c "
                "LEFT JOIN knowledge.human_reviews hr ON hr.classification_id = c.id "
                "WHERE hr.id IS NULL"
            )
        ).scalar()
        or 0
    )

    acceptance_rate = (accepted_count / total_reviews) if total_reviews > 0 else 0.0

    return {
        "total_reviews": total_reviews,
        "accepted_count": accepted_count,
        "modified_count": modified_count,
        "acceptance_rate": round(acceptance_rate, 4),
        "unreviewed_classifications": unreviewed_classifications,
    }


def incorporate_feedback_to_gold_dataset(
    connection: Connection,
    *,
    dataset_version_id: uuid.UUID,
    review_ids: list[uuid.UUID] | None = None,
) -> dict:
    """Synchronizes human reviews into the Gold Dataset (knowledge.gold_labels).

    For each reviewed tender:
    - If already in gold_labels for dataset_version_id: updates relevant, category_id, subcategory_id, notes, labeled_by.
    - If not in gold_labels: inserts a new row.
    - Ensures knowledge.documents has the preprocessed document ready for model training.
    - Updates dataset_versions.record_count and manifest.
    """
    # Fetch reviews to incorporate
    query = (
        "SELECT hr.id, hr.classification_id, hr.reviewer_id, u.email AS reviewer_email, "
        "hr.accepted, hr.relevant, hr.category_id, hr.subcategory_id, hr.reason, "
        "hr.created_at, cl.licitacion_id, cl.taxonomy_version "
        "FROM knowledge.human_reviews hr "
        "JOIN knowledge.classifications cl ON cl.id = hr.classification_id "
        "JOIN users u ON u.id = hr.reviewer_id "
    )
    params: dict = {}
    if review_ids:
        query += "WHERE hr.id = ANY(:review_ids) "
        params["review_ids"] = review_ids

    rows = connection.execute(text(query), params).all()

    inserted_count = 0
    updated_count = 0
    touched_licitacion_ids: list[int] = []

    for row in rows:
        licitacion_id = row.licitacion_id
        touched_licitacion_ids.append(licitacion_id)

        labeled_by = f"human-review:{row.reviewer_email}"
        notes = row.reason or ("Human review accepted" if row.accepted else "Human review modified")

        existing_gold = connection.execute(
            text(
                "SELECT id FROM knowledge.gold_labels "
                "WHERE dataset_version_id = :dataset_version_id AND licitacion_id = :licitacion_id"
            ),
            {"dataset_version_id": dataset_version_id, "licitacion_id": licitacion_id},
        ).first()

        if existing_gold:
            connection.execute(
                text(
                    "UPDATE knowledge.gold_labels SET "
                    "relevant = :relevant, category_id = :category_id, subcategory_id = :subcategory_id, "
                    "taxonomy_version = :taxonomy_version, labeled_by = :labeled_by, labeled_at = :labeled_at, "
                    "notes = :notes, updated_at = now() "
                    "WHERE id = :id"
                ),
                {
                    "relevant": row.relevant,
                    "category_id": row.category_id,
                    "subcategory_id": row.subcategory_id,
                    "taxonomy_version": row.taxonomy_version,
                    "labeled_by": labeled_by,
                    "labeled_at": row.created_at,
                    "notes": notes,
                    "id": existing_gold[0],
                },
            )
            updated_count += 1
        else:
            connection.execute(
                text(
                    "INSERT INTO knowledge.gold_labels "
                    "(id, dataset_version_id, licitacion_id, relevant, category_id, subcategory_id, taxonomy_version, labeled_by, labeled_at, notes, created_at, updated_at) "
                    "VALUES (:id, :dataset_version_id, :licitacion_id, :relevant, :category_id, :subcategory_id, :taxonomy_version, :labeled_by, :labeled_at, :notes, now(), now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "dataset_version_id": dataset_version_id,
                    "licitacion_id": licitacion_id,
                    "relevant": row.relevant,
                    "category_id": row.category_id,
                    "subcategory_id": row.subcategory_id,
                    "taxonomy_version": row.taxonomy_version,
                    "labeled_by": labeled_by,
                    "labeled_at": row.created_at,
                    "notes": notes,
                },
            )
            inserted_count += 1

    # Ensure preprocessed document exists for these tenders so classifier training can use them
    if touched_licitacion_ids:
        ensure_documents(connection, touched_licitacion_ids)

    # Update record_count and manifest in dataset_versions
    total_records = int(
        connection.execute(
            text("SELECT count(*) FROM knowledge.gold_labels WHERE dataset_version_id = :dataset_version_id"),
            {"dataset_version_id": dataset_version_id},
        ).scalar()
        or 0
    )

    ver_row = connection.execute(
        text("SELECT manifest FROM knowledge.dataset_versions WHERE id = :id"),
        {"id": dataset_version_id},
    ).first()

    manifest = json.loads(ver_row.manifest) if ver_row and ver_row.manifest else {}
    manifest["human_review_feedback"] = {
        "last_sync_at": datetime.now(timezone.utc).isoformat(),
        "synced_reviews_count": len(rows),
        "inserted_count": inserted_count,
        "updated_count": updated_count,
    }

    connection.execute(
        text(
            "UPDATE knowledge.dataset_versions SET "
            "record_count = :record_count, manifest = :manifest, updated_at = now() "
            "WHERE id = :id"
        ),
        {"record_count": total_records, "manifest": json.dumps(manifest), "id": dataset_version_id},
    )

    return {
        "dataset_version_id": str(dataset_version_id),
        "inserted": inserted_count,
        "updated": updated_count,
        "total_synced": inserted_count + updated_count,
        "record_count": total_records,
    }
