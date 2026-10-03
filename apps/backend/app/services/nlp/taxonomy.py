"""Taxonomy application service (Fase 6.18)."""

from __future__ import annotations

from typing import Any

from app.nlp.taxonomy import (
    DomainConcept,
    Taxonomy,
    TaxonomyCategory,
    TaxonomySubcategory,
    load_initial_taxonomy,
)
from app.repositories.knowledge import TaxonomyRepository


class TaxonomyService:
    def __init__(
        self,
        taxonomy: Taxonomy | None = None,
        taxonomy_repository: TaxonomyRepository | None = None,
    ) -> None:
        self._taxonomy = taxonomy or load_initial_taxonomy()
        self._taxonomy_repo = taxonomy_repository

    def resolve_category(self, code: str) -> TaxonomyCategory | None:
        for cat in self._taxonomy.categories:
            if cat.code == code:
                return cat
        return None

    def resolve_subcategory(
        self, category_code: str, subcategory_code: str
    ) -> TaxonomySubcategory | None:
        cat = self.resolve_category(category_code)
        if cat is None:
            return None
        for sub in cat.subcategories:
            if sub.code == subcategory_code:
                return sub
        return None

    def locate_concept(
        self, concept_code: str
    ) -> tuple[TaxonomyCategory, TaxonomySubcategory, DomainConcept] | None:
        try:
            return self._taxonomy.locate(concept_code)
        except KeyError:
            return None

    def get_hierarchy(self) -> dict[str, Any]:
        return {
            "version": self._taxonomy.version,
            "categories": [
                {
                    "code": cat.code,
                    "name": cat.name,
                    "description": cat.description,
                    "subcategories": [
                        {
                            "code": sub.code,
                            "name": sub.name,
                            "description": sub.description,
                            "concepts": [
                                {"code": c.code, "name": c.name, "description": c.description}
                                for c in sub.concepts
                            ],
                        }
                        for sub in cat.subcategories
                    ],
                }
                for cat in self._taxonomy.categories
            ],
        }

    def validate(self) -> list[str]:
        try:
            self._taxonomy.validate()
            return []
        except ValueError as exc:
            return [str(exc)]

    def get_version(self) -> str:
        return self._taxonomy.version
