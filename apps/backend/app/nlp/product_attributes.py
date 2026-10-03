"""Regex/keyword-based product attribute extraction from item text (6.12).

Same philosophy as app/nlp/entities.py (6.11): high precision, low
coverage on purpose. Materiales and características técnicas use a
controlled, documented, extensible keyword list rather than a
capitalization/POS heuristic — without a gold dataset (6.13) to validate
against, that kind of heuristic is noisy on real Chilean tender text
(same lesson learned with marca/modelo in 6.11).

Cantidad/unidad are NOT extracted here: they're already structured on
core.licitacion_item.cantidad/unidad (populated since 6.2 from the real
ChileCompra item payload, app/etl/loading/core_schema.py) — the caller
copies them directly instead of re-deriving them from text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MATERIALES = (
    "acero inoxidable", "acero", "aluminio", "madera", "plastico", "plástico", "pvc",
    "vidrio", "goma", "caucho", "cuero", "tela", "nylon", "fibra de carbono",
)
_CARACTERISTICAS_TECNICAS = (
    "plegable", "regulable en altura", "reclinable", "electrico", "eléctrico", "manual",
    "con freno", "antideslizante", "impermeable",
)

_DIMENSIONES_3D_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:cm|mm|m)\s*x\s*\d+(?:[.,]\d+)?\s*(?:cm|mm|m)"
    r"(?:\s*x\s*\d+(?:[.,]\d+)?\s*(?:cm|mm|m))?\b",
    re.IGNORECASE,
)
_DIMENSION_1D_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:cm|mm|m)\s*de\s*(?:ancho|alto|largo|profundidad)\b",
    re.IGNORECASE,
)
_CAPACIDAD_PATTERN = re.compile(
    r"\b(?:capacidad(?:\s*(?:de\s*)?(?:carga|peso))?|hasta)\s*(?:de\s*)?"
    r"(\d+(?:[.,]\d+)?\s*(?:kg|kilos|litros|l))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ProductAttributes:
    materiales: tuple[str, ...]
    dimensiones: str | None
    capacidad: str | None
    caracteristicas_tecnicas: tuple[str, ...]


def extract_product_attributes(item_text: str) -> ProductAttributes:
    materiales = _find_keywords(item_text, _MATERIALES)
    caracteristicas = _find_keywords(item_text, _CARACTERISTICAS_TECNICAS)

    dimension_match = _DIMENSIONES_3D_PATTERN.search(item_text) or _DIMENSION_1D_PATTERN.search(item_text)
    dimensiones = dimension_match.group(0) if dimension_match else None

    capacidad_match = _CAPACIDAD_PATTERN.search(item_text)
    capacidad = capacidad_match.group(1) if capacidad_match else None

    return ProductAttributes(materiales, dimensiones, capacidad, caracteristicas)


def _find_keywords(item_text: str, vocabulary: tuple[str, ...]) -> tuple[str, ...]:
    """Word-boundary match, longest-keyword-first, so "acero" doesn't
    double-count inside an already-matched "acero inoxidable" (same class
    of substring bug fixed for marca/modelo in 6.11 — \\b keeps "manual"
    from matching inside "manualidades", "acero" inside "aceros", etc.)."""
    found: list[str] = []
    remaining = item_text
    for keyword in sorted(vocabulary, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        match = pattern.search(remaining)
        if match:
            found.append(keyword)
            remaining = remaining[:match.start()] + remaining[match.end():]
    return tuple(keyword for keyword in vocabulary if keyword in found)
