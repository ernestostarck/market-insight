"""Get-or-create helpers for persisting taxonomy nodes referenced by an NLP
stage result. Shared by `ClassificationStageExecutor` and
`EmbeddingsStageExecutor` — both resolve a `Taxonomy` category/subcategory
code into a `knowledge.categories`/`knowledge.subcategories` row on demand
(there is no separate seed step; the tables populate themselves the first
time a real classification touches a given node)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.taxonomy import Taxonomy


def resolve_category(connection: Connection, taxonomy: Taxonomy, code: str) -> int:
    row = connection.execute(
        text("SELECT id FROM knowledge.categories WHERE code = :code AND taxonomy_version = :taxonomy_version"),
        {"code": code, "taxonomy_version": taxonomy.version},
    ).first()
    if row is not None:
        return int(row[0])
    category = taxonomy.category(code)
    inserted = connection.execute(
        text(
            "INSERT INTO knowledge.categories (code, name, description, taxonomy_version, active) "
            "VALUES (:code, :name, :description, :taxonomy_version, true) RETURNING id"
        ),
        {
            "code": code, "name": category.name, "description": category.description,
            "taxonomy_version": taxonomy.version,
        },
    ).first()
    return int(inserted[0])


def resolve_subcategory(
    connection: Connection, taxonomy: Taxonomy, category_id: int, category_code: str, code: str,
) -> int:
    row = connection.execute(
        text(
            "SELECT id FROM knowledge.subcategories "
            "WHERE category_id = :category_id AND code = :code AND taxonomy_version = :taxonomy_version"
        ),
        {"category_id": category_id, "code": code, "taxonomy_version": taxonomy.version},
    ).first()
    if row is not None:
        return int(row[0])
    category = taxonomy.category(category_code)
    subcategory = next(sub for sub in category.subcategories if sub.code == code)
    inserted = connection.execute(
        text(
            "INSERT INTO knowledge.subcategories (category_id, code, name, description, taxonomy_version, active) "
            "VALUES (:category_id, :code, :name, :description, :taxonomy_version, true) RETURNING id"
        ),
        {
            "category_id": category_id, "code": code, "name": subcategory.name,
            "description": subcategory.description, "taxonomy_version": taxonomy.version,
        },
    ).first()
    return int(inserted[0])
