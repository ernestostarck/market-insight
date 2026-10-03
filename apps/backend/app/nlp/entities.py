"""Regex-based entity extraction from already-normalized text (Fase 6.11).

Structured entities (organismo, ubicacion, producto) are NOT extracted
here — they're already known from `core.licitacion`/`core.organismo`/
`core.licitacion_item` and are projected directly by
`app/nlp/knowledge_stage.py`. This module only covers what genuinely
requires reading free text: cantidad+unidad, fecha, monto, marca, modelo.

Confidence is an initial, documented heuristic (same spirit as
`_RULE_SCORE_SATURATION`/`_SIMILARITY_THRESHOLD` in 6.7/6.8): 0.9 for the
unambiguous numeric/date/amount patterns, 0.6 for marca/modelo — those
only fire on an explicit "marca"/"modelo" keyword (high precision, low
coverage on purpose; no capitalization heuristics, which would be noisy
without a gold dataset to validate against).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CONFIDENCE_NUMERIC = 0.9
_CONFIDENCE_BRAND = 0.6

_CANTIDAD_UNIDAD_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(kg|m2|m|l|unidades|unidad)\b", re.IGNORECASE
)
_FECHA_NUMERIC_PATTERN = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_MESES = (
    "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre"
)
_FECHA_LARGA_PATTERN = re.compile(
    rf"\b(\d{{1,2}}) de ({_MESES}) de (\d{{4}})\b", re.IGNORECASE
)
_MONTO_SIGNO_PATTERN = re.compile(r"\$\s?\d(?:[\d.,]*\d)?")
_MONTO_PALABRA_PATTERN = re.compile(r"\b\d(?:[\d.,]*\d)?\s*(pesos|UF|UTM)\b", re.IGNORECASE)
_MARCA_PATTERN = re.compile(
    r"\bmarca\b\s*[:\-]?\s*((?:(?!\bmodelo\b)[\w-]+\s*){1,3})", re.IGNORECASE
)
_MODELO_PATTERN = re.compile(
    r"\bmodelo\b\s*[:\-]?\s*((?:(?!\bmarca\b)[\w-]+\s*){1,3})", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    entity_type: str
    value: str
    normalized_value: str | None
    confidence_score: float
    start_offset: int | None = None
    end_offset: int | None = None


def extract_text_entities(normalized_text: str) -> tuple[ExtractedEntity, ...]:
    entities: list[ExtractedEntity] = []

    for match in _CANTIDAD_UNIDAD_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "cantidad", match.group(0), match.group(1).replace(",", "."),
            _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))
        entities.append(ExtractedEntity(
            "unidad", match.group(0), _normalize_unidad(match.group(2)),
            _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))

    for match in _FECHA_NUMERIC_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "fecha", match.group(0), None, _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))
    for match in _FECHA_LARGA_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "fecha", match.group(0), None, _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))

    for match in _MONTO_SIGNO_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "monto", match.group(0), None, _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))
    for match in _MONTO_PALABRA_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "monto", match.group(0), None, _CONFIDENCE_NUMERIC, match.start(), match.end(),
        ))

    for match in _MARCA_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "marca", match.group(1).strip(), None, _CONFIDENCE_BRAND, match.start(), match.end(),
        ))
    for match in _MODELO_PATTERN.finditer(normalized_text):
        entities.append(ExtractedEntity(
            "modelo", match.group(1).strip(), None, _CONFIDENCE_BRAND, match.start(), match.end(),
        ))

    return tuple(entities)


def _normalize_unidad(raw: str) -> str:
    lowered = raw.lower()
    return "unidad" if lowered.startswith("unidad") else lowered
