"""Core (Connection + text()) persistence for trained classifiers (6.14).

Same style as app/nlp/taxonomy_db.py / gold_dataset_db.py.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection


def register_model_version(
    connection: Connection,
    *,
    name: str,
    version: str,
    kind: str = "classifier",
    status: str,
    parameters: dict,
    metrics: dict,
) -> uuid.UUID:
    """Get-or-create by (name, version) — same pattern as
    resolve_category (app/nlp/taxonomy_db.py). Re-registering the same
    name+version updates status/parameters/metrics in place (retraining
    the same version, e.g. after a bugfix, doesn't create a duplicate)."""
    row = connection.execute(
        text("SELECT id FROM knowledge.model_versions WHERE name = :name AND version = :version"),
        {"name": name, "version": version},
    ).first()
    if row is not None:
        connection.execute(
            text(
                "UPDATE knowledge.model_versions SET status = :status, parameters = :parameters, "
                "metrics = :metrics, updated_at = now() WHERE id = :id"
            ),
            {"status": status, "parameters": json.dumps(parameters), "metrics": json.dumps(metrics), "id": row[0]},
        )
        return row[0]

    model_version_id = uuid.uuid4()
    connection.execute(
        text(
            "INSERT INTO knowledge.model_versions (id, name, version, kind, status, parameters, metrics) "
            "VALUES (:id, :name, :version, :kind, :status, :parameters, :metrics)"
        ),
        {
            "id": model_version_id, "name": name, "version": version, "kind": kind, "status": status,
            "parameters": json.dumps(parameters), "metrics": json.dumps(metrics),
        },
    )
    return model_version_id


def latest_production_or_staging_classifier(connection: Connection) -> dict | None:
    """The classifier 6.15 loads for inference: the most recent
    `production` ModelVersion of kind='classifier' if one exists,
    otherwise the most recent `staging` one, otherwise None (the hybrid
    pipeline runs fine without a model — rules + semantic only, same as
    before 6.14)."""
    for status in ("production", "staging"):
        row = connection.execute(
            text(
                "SELECT id, name, version, artifact_uri, parameters FROM knowledge.model_versions "
                "WHERE kind = 'classifier' AND status = :status ORDER BY created_at DESC LIMIT 1"
            ),
            {"status": status},
        ).first()
        if row is not None:
            return {
                "id": row.id, "name": row.name, "version": row.version,
                "artifact_uri": row.artifact_uri, "parameters": row.parameters,
            }
    return None


def set_artifact_uri(connection: Connection, model_version_id: uuid.UUID, artifact_uri: str) -> None:
    connection.execute(
        text("UPDATE knowledge.model_versions SET artifact_uri = :artifact_uri, updated_at = now() WHERE id = :id"),
        {"artifact_uri": artifact_uri, "id": model_version_id},
    )
