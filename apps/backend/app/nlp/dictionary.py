"""Versioned domain dictionary: geriatría, discapacidad, accesibilidad, etc.

Same loading pattern as app/nlp/taxonomy.py (load_initial_taxonomy). Unlike
the taxonomy, most entries here have no category_code/subcategory_code: the
9 required themes are cross-cutting populations/topics (a wheelchair is both
"salud/equipamiento-médico" and "discapacidad"), not product categories, so
they don't map 1:1 onto the taxonomy's 6 sectors. See
docs/07-ai/semantic-dictionary.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files

from app.nlp.contracts import DictionaryVersion
from app.nlp.taxonomy import Taxonomy, load_initial_taxonomy


class DomainTheme(StrEnum):
    GERIATRIA = "geriatria"
    ADULTOS_MAYORES = "adultos_mayores"
    DISCAPACIDAD = "discapacidad"
    MOVILIDAD_REDUCIDA = "movilidad_reducida"
    ACCESIBILIDAD = "accesibilidad"
    AYUDAS_TECNICAS = "ayudas_tecnicas"
    PREVENCION_CAIDAS = "prevencion_caidas"
    REHABILITACION = "rehabilitacion"
    ADAPTACION_ESPACIOS = "adaptacion_espacios"


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    concept: str
    theme: DomainTheme
    term: str
    synonyms: tuple[str, ...] = field(default_factory=tuple)
    abbreviations: tuple[str, ...] = field(default_factory=tuple)
    category_code: str | None = None
    subcategory_code: str | None = None
    weight: float = 1.0

    def all_surface_forms(self) -> tuple[str, ...]:
        return (self.term, *self.synonyms, *self.abbreviations)


@dataclass(frozen=True, slots=True)
class DomainDictionary:
    version: str
    entries: tuple[DictionaryEntry, ...]

    def validate(self, taxonomy: Taxonomy | None = None) -> None:
        DictionaryVersion(self.version)

        themes_covered = {entry.theme for entry in self.entries}
        missing_themes = set(DomainTheme) - themes_covered
        if missing_themes:
            raise ValueError(f"missing entries for theme(s): {sorted(missing_themes)}")

        concepts = [entry.concept for entry in self.entries]
        if len(concepts) != len(set(concepts)):
            raise ValueError("duplicate concept in domain dictionary")

        surface_forms = [
            form.strip().casefold()
            for entry in self.entries
            for form in entry.all_surface_forms()
        ]
        if len(surface_forms) != len(set(surface_forms)):
            raise ValueError("duplicate surface form (term/synonym/abbreviation) in domain dictionary")

        for entry in self.entries:
            if not entry.term.strip():
                raise ValueError(f"concept '{entry.concept}' has an empty term")
            if entry.subcategory_code and not entry.category_code:
                raise ValueError(f"concept '{entry.concept}' has subcategory_code without category_code")
            if taxonomy is not None and entry.category_code:
                self._validate_category(taxonomy, entry)

    @staticmethod
    def _validate_category(taxonomy: Taxonomy, entry: "DictionaryEntry") -> None:
        try:
            category = taxonomy.category(entry.category_code)  # type: ignore[arg-type]
        except StopIteration as exc:
            raise ValueError(
                f"concept '{entry.concept}' references unknown category_code '{entry.category_code}'"
            ) from exc
        if entry.subcategory_code and not any(
            sub.code == entry.subcategory_code for sub in category.subcategories
        ):
            raise ValueError(
                f"concept '{entry.concept}' references unknown subcategory_code "
                f"'{entry.subcategory_code}' under category '{entry.category_code}'"
            )


def load_initial_dictionary() -> DomainDictionary:
    payload = json.loads(files("app.nlp").joinpath("data/dictionary-2026.1.json").read_text(encoding="utf-8"))
    dictionary = DomainDictionary(
        version=payload["version"],
        entries=tuple(
            DictionaryEntry(
                concept=item["concept"],
                theme=DomainTheme(item["theme"]),
                term=item["term"],
                synonyms=tuple(item.get("synonyms", ())),
                abbreviations=tuple(item.get("abbreviations", ())),
                category_code=item.get("category_code"),
                subcategory_code=item.get("subcategory_code"),
                weight=item.get("weight", 1.0),
            )
            for item in payload["entries"]
        ),
    )
    dictionary.validate(load_initial_taxonomy())
    return dictionary
