"""Get-or-create helper for `knowledge.product_concepts` (Fase 6.12).

Same pattern as `app/nlp/taxonomy_db.py::resolve_category`/
`resolve_subcategory`: the table self-populates the first time a real
product match touches a given concept, no separate seed step.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.nlp.dictionary import DomainDictionary


def resolve_product_concept(
    connection: Connection,
    dictionary: DomainDictionary,
    concept_code: str,
    category_id: int,
    subcategory_id: int,
) -> int:
    row = connection.execute(
        text(
            "SELECT id FROM knowledge.product_concepts "
            "WHERE code = :code AND dictionary_version = :dictionary_version"
        ),
        {"code": concept_code, "dictionary_version": dictionary.version},
    ).first()
    if row is not None:
        return int(row[0])
    inserted = connection.execute(
        text(
            "INSERT INTO knowledge.product_concepts (code, category_id, subcategory_id, dictionary_version) "
            "VALUES (:code, :category_id, :subcategory_id, :dictionary_version) RETURNING id"
        ),
        {
            "code": concept_code, "category_id": category_id, "subcategory_id": subcategory_id,
            "dictionary_version": dictionary.version,
        },
    ).first()
    return int(inserted[0])
