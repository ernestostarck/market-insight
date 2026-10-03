"""Deterministic keyword rules for the apparel/shapewear product line.

This is a separate business line from the geriatric/disability/accessibility
market the rest of `app/nlp` is built around (confirmed with the user):
shapewear has no connection to any of the 9 cross-cutting population themes
in `app/nlp/dictionary.py` (`DomainTheme`), so it does not go through
`DomainDictionary`/`build_ruleset()`. It plugs directly into the taxonomy's
`apparel/shapewear` node (`taxonomy-2026.3`) with its own small, explicit
rule set — the same `Rule` shape `build_ruleset()` produces, just built by
hand instead of generated from a versioned dictionary, since this line
doesn't need one yet.
"""

from __future__ import annotations

from app.nlp.rules import Rule

VERSION = "apparel-2026.1"

_CATEGORY_CODE = "apparel"
_SUBCATEGORY_CODE = "shapewear"

# (concept_code, canonical term, synonyms) — concept codes match the
# DomainConcept codes under taxonomy-2026.3's apparel/shapewear subcategory.
# Matching is plain substring (see RuleEngine.evaluate), so Spanish plurals
# need their own explicit surface form — "faja" does not match "fajas".
_CONCEPTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "faja_reductora",
        "faja reductora",
        (
            "fajas reductoras", "faja moldeadora", "fajas moldeadoras",
            "body moldeador", "body moldeadora", "faja body moldeadora", "fajas body moldeadora",
        ),
    ),
    (
        "faja_moldeadora_short",
        "faja moldeadora tipo short",
        (
            "fajas moldeadoras tipo short", "moldeadora tipo short sin costuras",
            "short sin costuras", "tipo short sin costuras",
        ),
    ),
    (
        "faja_moldeadora_colaless",
        "faja moldeadora tipo colaless",
        (
            "fajas moldeadoras tipo colaless", "moldeadora tipo colaless",
            "tipo colaless", "colaless con cierre frontal", "faja colaless",
        ),
    ),
)


def build_apparel_ruleset() -> tuple[Rule, ...]:
    """One `Rule` per surface form (term + synonyms) of every concept above."""
    rules: list[Rule] = []
    for concept_code, term, synonyms in _CONCEPTS:
        for index, surface_form in enumerate((term, *synonyms)):
            rules.append(Rule(
                id=f"{VERSION}:{concept_code}:{index}",
                concept_code=concept_code,
                category_code=_CATEGORY_CODE,
                subcategory_code=_SUBCATEGORY_CODE,
                keyword=surface_form,
                version=VERSION,
            ))
    return tuple(rules)
