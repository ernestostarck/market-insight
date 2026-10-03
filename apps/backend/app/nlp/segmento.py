"""Market segment ("segmento") scoping for the whole API.

A segmento is a rubro (taxonomy category, ``cat:<code>``) or a single concept
(``concept:<code>``) picked on the Rubros page. It resolves to the surface forms
that describe it — concept names, the domain dictionary's terms/synonyms
(app/nlp/dictionary.py) and the apparel keyword rules (app/nlp/apparel_rules.py) —
which are matched with ILIKE against licitacion nombre/descripcion, the same
approach "Mercado Objetivo" uses (only ~150 licitaciones have an NLP
classification so far). A rubro with no concepts falls back to its
subcategory names.

The matching licitacion ids are cached in-process for a few minutes: the
dashboard fires several segment-scoped requests at once and the ILIKE scan
costs ~2 s.
"""

from __future__ import annotations

import asyncio
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import ColumnElement, Integer, any_, literal, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core.licitacion import Licitacion
from app.nlp.apparel_rules import build_apparel_ruleset
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.taxonomy import load_initial_taxonomy

_IDS_TTL_SECONDS = 600
_ids_cache: dict[str, tuple[float, list[int]]] = {}
_ids_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass(frozen=True)
class Segmento:
    code: str
    label: str
    terms: tuple[str, ...]


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
    )


def _normalize(forms: set[str]) -> tuple[str, ...]:
    # Postgres ILIKE is case- but not accent-insensitive, so match both spellings.
    terms = {form.strip().lower() for form in forms if form and form.strip()}
    terms |= {_strip_accents(term) for term in terms}
    return tuple(sorted(terms))


def _concept_forms(code: str, name: str) -> set[str]:
    forms = {name}
    forms |= {
        form
        for entry in load_initial_dictionary().entries
        if entry.concept == code
        for form in entry.all_surface_forms()
    }
    forms |= {rule.keyword for rule in build_apparel_ruleset() if rule.concept_code == code}
    return forms


@lru_cache(maxsize=128)
def resolve_segmento(code: str) -> Segmento | None:
    kind, _, value = code.strip().partition(":")
    taxonomy = load_initial_taxonomy()

    if kind == "concept":
        try:
            _, _, concept = taxonomy.locate(value)
        except KeyError:
            return None
        return Segmento(code, concept.name, _normalize(_concept_forms(concept.code, concept.name)))

    if kind == "cat":
        category = next((c for c in taxonomy.categories if c.code == value), None)
        if category is None:
            return None
        forms = {sub.name for sub in category.subcategories}
        for sub in category.subcategories:
            for concept in sub.concepts:
                forms |= _concept_forms(concept.code, concept.name)
        forms |= {
            form
            for entry in load_initial_dictionary().entries
            if entry.category_code == category.code
            for form in entry.all_surface_forms()
        }
        return Segmento(code, category.name, _normalize(forms))

    return None


def terms_filter(terms: tuple[str, ...]) -> ColumnElement[bool]:
    conditions = []
    for term in terms:
        pattern = f"%{term}%"
        conditions.append(Licitacion.nombre.ilike(pattern))
        conditions.append(Licitacion.descripcion.ilike(pattern))
    return or_(*conditions)


def id_in(column: ColumnElement[int], ids: list[int]) -> ColumnElement[bool]:
    """`column = ANY(:ids)` — one array bind instead of thousands of IN params."""
    return column == any_(literal(ids, ARRAY(Integer)))


async def licitacion_ids_for(session: AsyncSession, segmento: Segmento) -> list[int]:
    cached = _ids_cache.get(segmento.code)
    if cached and time.monotonic() - cached[0] < _IDS_TTL_SECONDS:
        return cached[1]
    async with _ids_locks[segmento.code]:
        cached = _ids_cache.get(segmento.code)
        if cached and time.monotonic() - cached[0] < _IDS_TTL_SECONDS:
            return cached[1]
        result = await session.execute(select(Licitacion.id).where(terms_filter(segmento.terms)))
        ids = list(result.scalars().all())
        _ids_cache[segmento.code] = (time.monotonic(), ids)
        return ids
