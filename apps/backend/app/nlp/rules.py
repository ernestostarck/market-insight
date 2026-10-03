"""Versioned, deterministic keyword rules for clear classification cases."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from app.nlp.dictionary import DomainDictionary
from app.nlp.taxonomy import Taxonomy


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    concept_code: str
    category_code: str
    keyword: str
    weight: float = 1.0
    version: str = "1"
    subcategory_code: str | None = None
    active: bool = True
    is_regex: bool = False


@dataclass(frozen=True, slots=True)
class RuleMatch:
    rule_id: str
    keyword: str
    concept_code: str
    category_code: str
    subcategory_code: str | None
    weight: float
    version: str


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    category_code: str | None
    subcategory_code: str | None
    score: float
    matches: tuple[RuleMatch, ...]


class RuleEngine:
    """Score active keyword/regex rules against already-normalized text."""

    def __init__(self, rules: tuple[Rule, ...] | list[Rule] = ()) -> None:
        self._rules = tuple(rules)
        self._patterns: dict[str, re.Pattern[str]] = {
            rule.id: re.compile(rule.keyword, re.IGNORECASE)
            for rule in self._rules
            if rule.is_regex
        }

    def evaluate(self, normalized_text: str) -> RuleEvaluation:
        matches: list[RuleMatch] = []
        scores: defaultdict[tuple[str, str | None], float] = defaultdict(float)
        text = normalized_text.casefold()
        for rule in self._rules:
            if not rule.active:
                continue
            if rule.is_regex:
                found = bool(self._patterns[rule.id].search(normalized_text))
            else:
                keyword = rule.keyword.strip().casefold()
                found = bool(keyword) and keyword in text
            if found:
                match = RuleMatch(
                    rule.id, rule.keyword, rule.concept_code, rule.category_code,
                    rule.subcategory_code, rule.weight, rule.version,
                )
                matches.append(match)
                scores[(rule.category_code, rule.subcategory_code)] += rule.weight
        if not scores:
            return RuleEvaluation(None, None, 0.0, tuple())
        (category_code, subcategory_code), score = max(
            scores.items(), key=lambda item: (item[1], item[0][0], item[0][1] or "")
        )
        return RuleEvaluation(category_code, subcategory_code, score, tuple(matches))


def build_ruleset(dictionary: DomainDictionary, taxonomy: Taxonomy) -> tuple[Rule, ...]:
    """Generate the initial rule set: one `Rule` per surface form of every
    dictionary entry. `concept_code` is always `entry.theme.value` (the 6.5
    bridge). `category_code`/`subcategory_code` use the entry's own
    product-specific values when set, otherwise the concept's home in the
    taxonomy (`Taxonomy.locate`)."""
    rules: list[Rule] = []
    for entry in dictionary.entries:
        concept_code = entry.theme.value
        if entry.category_code:
            category_code = entry.category_code
            subcategory_code = entry.subcategory_code
        else:
            category, subcategory, _ = taxonomy.locate(concept_code)
            category_code, subcategory_code = category.code, subcategory.code

        # Abbreviations are short (2-5 chars) and match as substrings of
        # unrelated words with plain "in" search (e.g. "to" inside
        # "auditorio", "servicio", "contrato") — real ChileCompra data
        # confirmed this false-positive during 6.7 validation. Terms and
        # synonyms are full multi-word phrases, safe as substrings.
        surface_forms = (
            [(form, False) for form in (entry.term, *entry.synonyms)]
            + [(form, True) for form in entry.abbreviations]
        )
        for index, (surface_form, is_abbreviation) in enumerate(surface_forms):
            rules.append(Rule(
                id=f"{dictionary.version}:{entry.concept}:{index}",
                concept_code=concept_code,
                category_code=category_code,
                subcategory_code=subcategory_code,
                keyword=rf"\b{re.escape(surface_form)}\b" if is_abbreviation else surface_form,
                weight=entry.weight,
                version=dictionary.version,
                is_regex=is_abbreviation,
            ))
    return tuple(rules)
