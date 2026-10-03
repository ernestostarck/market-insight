"""Product-concept matching against item text (Fase 6.12).

A `product_concept` is simply a `DictionaryEntry` with `category_code`
set: most dictionary entries (app/nlp/dictionary.py) describe cross-
cutting populations/topics (geriatría, discapacidad, rehabilitación) with
no `category_code`, but 16 entries already describe tangible goods/works
(silla de ruedas, andador, rampa de acceso, ...) and carry a real
`category_code`/`subcategory_code` — that's the exact signal that
distinguishes "this is a product" from "this is a topic". No new catalog,
no change to `dictionary.py`.

This does NOT reuse `RuleEngine`/`build_ruleset` (app/nlp/rules.py):
those aggregate matches to a single winning category/subcategory per
whole document (`RuleMatch.concept_code` is the cross-cutting theme, not
the specific product concept). Here we want every product an item
mentions, independently, so a plain per-entry substring scan is simpler
and correct for this shape of problem.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.nlp.dictionary import DictionaryEntry, DomainDictionary


@dataclass(frozen=True, slots=True)
class ProductConceptMatch:
    concept_code: str
    category_code: str
    subcategory_code: str
    matched_term: str
    start_offset: int
    end_offset: int


def product_concept_entries(dictionary: DomainDictionary) -> tuple[DictionaryEntry, ...]:
    return tuple(entry for entry in dictionary.entries if entry.category_code is not None)


def match_product_concepts(item_text: str, dictionary: DomainDictionary) -> tuple[ProductConceptMatch, ...]:
    matches: list[ProductConceptMatch] = []
    lowered = item_text.casefold()
    for entry in product_concept_entries(dictionary):
        for surface_form in entry.all_surface_forms():
            needle = surface_form.strip().casefold()
            if not needle:
                continue
            start = lowered.find(needle)
            if start == -1:
                continue
            matches.append(ProductConceptMatch(
                concept_code=entry.concept,
                category_code=entry.category_code,  # type: ignore[arg-type]
                subcategory_code=entry.subcategory_code,  # type: ignore[arg-type]
                matched_term=surface_form,
                start_offset=start,
                end_offset=start + len(needle),
            ))
            break  # one match per concept per item is enough to identify it
    return tuple(matches)
