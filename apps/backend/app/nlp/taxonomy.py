"""Versioned taxonomy loading and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib.resources import files

# "_" allowed alongside kebab-case: concept codes reuse DomainTheme's
# snake_case values (app/nlp/dictionary.py) so a concept is the same string
# as its dictionary theme — no indirect mapping table needed between them.
_STABLE_CODE = re.compile(r"^[a-z][a-z0-9_-]{1,99}$")

_LATEST_VERSION = "2026.3"


@dataclass(frozen=True, slots=True)
class DomainConcept:
    code: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class TaxonomySubcategory:
    code: str
    name: str
    description: str
    concepts: tuple[DomainConcept, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TaxonomyCategory:
    code: str
    name: str
    description: str
    subcategories: tuple[TaxonomySubcategory, ...]


@dataclass(frozen=True, slots=True)
class Taxonomy:
    version: str
    categories: tuple[TaxonomyCategory, ...]

    def validate(self) -> None:
        if not self.version.startswith("taxonomy-"):
            raise ValueError("taxonomy version must start with 'taxonomy-'")
        _validate_codes([category.code for category in self.categories], "category")

        all_concept_codes: list[str] = []
        for category in self.categories:
            if not category.name.strip() or not category.description.strip():
                raise ValueError(f"category '{category.code}' requires a name and description")
            _validate_codes([child.code for child in category.subcategories], f"subcategory of '{category.code}'")
            for child in category.subcategories:
                if not child.name.strip() or not child.description.strip():
                    raise ValueError(f"subcategory '{child.code}' requires a name and description")
                for concept in child.concepts:
                    if not concept.name.strip() or not concept.description.strip():
                        raise ValueError(f"concept '{concept.code}' requires a name and description")
                all_concept_codes.extend(concept.code for concept in child.concepts)
        # Global uniqueness (not just per-subcategory): concept codes double as
        # DomainTheme values (app/nlp/dictionary.py), which must be unique
        # across the whole dictionary regardless of which subcategory they live in.
        _validate_codes(all_concept_codes, "concept")

    def category(self, code: str) -> TaxonomyCategory:
        return next(category for category in self.categories if category.code == code)

    def concept(self, code: str) -> DomainConcept:
        return next(
            concept
            for category in self.categories
            for subcategory in category.subcategories
            for concept in subcategory.concepts
            if concept.code == code
        )

    def locate(self, concept_code: str) -> tuple[TaxonomyCategory, TaxonomySubcategory, DomainConcept]:
        """Find a concept's parent subcategory and category (6.7 needs this
        to turn a concept association into a category/subcategory one)."""
        for category in self.categories:
            for subcategory in category.subcategories:
                for concept in subcategory.concepts:
                    if concept.code == concept_code:
                        return category, subcategory, concept
        raise KeyError(f"no concept with code '{concept_code}' in taxonomy {self.version}")


def load_taxonomy(version: str = _LATEST_VERSION) -> Taxonomy:
    payload = json.loads(files("app.nlp").joinpath(f"data/taxonomy-{version}.json").read_text(encoding="utf-8"))
    taxonomy = Taxonomy(
        version=payload["version"],
        categories=tuple(
            TaxonomyCategory(
                code=item["code"], name=item["name"], description=item["description"],
                subcategories=tuple(
                    TaxonomySubcategory(
                        code=child["code"], name=child["name"], description=child["description"],
                        concepts=tuple(DomainConcept(**concept) for concept in child.get("concepts", [])),
                    )
                    for child in item["subcategories"]
                ),
            ) for item in payload["categories"]
        ),
    )
    taxonomy.validate()
    return taxonomy


def load_initial_taxonomy() -> Taxonomy:
    return load_taxonomy()


def _validate_codes(codes: list[str], kind: str) -> None:
    if len(codes) != len(set(codes)):
        raise ValueError(f"duplicate {kind} code")
    invalid = [code for code in codes if not _STABLE_CODE.fullmatch(code)]
    if invalid:
        raise ValueError(f"invalid {kind} code: {invalid[0]}")
