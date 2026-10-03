"""Dictionary application service (Fase 6.18)."""

from __future__ import annotations

from dataclasses import dataclass

from app.nlp.dictionary import (
    DictionaryEntry,
    DomainDictionary,
    DomainTheme,
    load_initial_dictionary,
)
from app.repositories.knowledge import DictionaryRepository


@dataclass(frozen=True, slots=True)
class DictionaryMatch:
    entry: DictionaryEntry
    surface_form: str
    start: int = -1
    end: int = -1


class DictionaryService:
    def __init__(
        self,
        dictionary: DomainDictionary | None = None,
        dictionary_repository: DictionaryRepository | None = None,
    ) -> None:
        self._dictionary = dictionary or load_initial_dictionary()
        self._dictionary_repo = dictionary_repository

    def find_matches(self, text: str) -> list[DictionaryMatch]:
        text_lower = text.casefold()
        matches: list[DictionaryMatch] = []
        for entry in self._dictionary.entries:
            for form in entry.all_surface_forms():
                f_lower = form.strip().casefold()
                if not f_lower:
                    continue
                start = 0
                while True:
                    pos = text_lower.find(f_lower, start)
                    if pos == -1:
                        break
                    matches.append(
                        DictionaryMatch(
                            entry=entry,
                            surface_form=form,
                            start=pos,
                            end=pos + len(f_lower),
                        )
                    )
                    start = pos + len(f_lower)
        return matches

    def get_entry(self, term: str) -> DictionaryEntry | None:
        term_clean = term.strip().casefold()
        for entry in self._dictionary.entries:
            if entry.term.strip().casefold() == term_clean:
                return entry
            if any(s.strip().casefold() == term_clean for s in entry.synonyms):
                return entry
            if any(a.strip().casefold() == term_clean for a in entry.abbreviations):
                return entry
        return None

    def list_terms(self, theme: DomainTheme | None = None) -> list[DictionaryEntry]:
        entries = self._dictionary.entries
        if theme is not None:
            return [e for e in entries if e.theme == theme]
        return list(entries)

    def get_version(self) -> str:
        return self._dictionary.version
