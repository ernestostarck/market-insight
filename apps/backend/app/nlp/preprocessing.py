"""Text normalization for procurement documents.

Pipeline order (see docs/07-ai/text-preprocessing.md for the full rationale):
None-coalesce -> HTML unescape+strip -> NFKC -> corruption/invisible-char
cleanup -> decorative symbol cleanup -> abbreviation normalization -> unit
normalization -> whitespace collapse -> casefold -> language detection.
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable

_WHITESPACE = re.compile(r"\s+")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Defensive cleanup for text that could arrive corrupted from a future source
# (e.g. OCR of documentos asociados) — not a fix for any corruption observed in
# ChileCompra's real API responses, which are correctly UTF-8 encoded (verified
# by inspecting raw bytes and decoded strings directly, see the doc above).
_REPLACEMENT_CHAR = re.compile("�+")
# Zero-width space/joiners (U+200B-200D), LTR/RTL marks (U+200E-200F),
# directional formatting chars (U+202A-202E), BOM (U+FEFF), soft hyphen
# (U+00AD). Built from chr() codepoints, not literal characters, since these
# are invisible in a source file and impossible to review by eye otherwise.
_INVISIBLE_CODEPOINTS = (
    list(range(0x200B, 0x200F + 1)) + list(range(0x202A, 0x202E + 1)) + [0xFEFF, 0x00AD]
)
_INVISIBLE_CHARS = re.compile("[" + "".join(chr(cp) for cp in _INVISIBLE_CODEPOINTS) + "]")

_DECORATIVE_SYMBOLS = re.compile("[•▪◦‣►▶➤]")

# "N°"/"Nº" only means "número" when immediately followed by a digit — without
# that guard this would corrupt the negation "No aplica" into "numero aplica".
# NFKC (applied earlier in the pipeline) already turns "Nº" into "No", so both
# the degree-sign and post-NFKC spellings need to be matched here.
_NUMERO_PATTERN = re.compile(r"\bn\s*[o°]\s*(?=\d)", re.IGNORECASE)

# "un"/"und"/"unid" collide with the indefinite article "un" ("a/an") and other
# words, so they're only treated as the unit "unidad" when directly attached to
# a preceding number (e.g. "10un", "10 und.") — never as a standalone word.
_UNIDAD_PATTERN = re.compile(r"(\d+)\s*un(?:id|d)?\b\.?", re.IGNORECASE)

_SIMPLE_UNIT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmts?2\b", re.IGNORECASE), "m2"),
    (re.compile(r"\bm2\b"), "m2"),
    (re.compile(r"\bkgs?\b\.?", re.IGNORECASE), "kg"),
    (re.compile(r"\bmts?\b\.?", re.IGNORECASE), "m"),
    (re.compile(r"\blts?\b\.?", re.IGNORECASE), "l"),
)

_SPANISH_MARKERS = frozenset({
    "de", "la", "el", "los", "las", "para", "con", "del", "por", "en", "que",
    "una", "uno", "se", "su", "sus", "al", "es", "y", "o",
    "adquisicion", "adquisición", "licitacion", "licitación",
    "compra", "servicio", "servicios", "contrato", "producto", "productos",
})


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append(" ")

    def get_text(self) -> str:
        return " ".join(self.parts)


@dataclass(frozen=True, slots=True)
class PreprocessedText:
    original_text: str
    normalized_text: str
    language: str


def tokenize(text: str) -> tuple[str, ...]:
    """Split already-normalized text into word tokens.

    Standalone — not part of `preprocess()`'s pipeline. Nothing consumes
    tokens yet (RuleEngine matches substrings); this is here for whichever
    future phase (e.g. 6.11 NER) needs word-level input.
    """
    return tuple(re.findall(r"[\wáéíóúñü]+", text))


class TextPreprocessor:
    """Normalize tender text without losing the source input."""

    def preprocess(self, text: str | None) -> PreprocessedText:
        original = text or ""
        parser = _HTMLToText()
        parser.feed(html.unescape(original))
        parser.close()

        normalized = unicodedata.normalize("NFKC", parser.get_text())
        normalized = _CONTROL_CHARS.sub(" ", normalized)
        normalized = _REPLACEMENT_CHAR.sub(" ", normalized)
        normalized = _INVISIBLE_CHARS.sub("", normalized)
        normalized = _DECORATIVE_SYMBOLS.sub(" ", normalized)
        normalized = _expand_abbreviations(normalized)
        normalized = _normalize_units(normalized)
        normalized = _WHITESPACE.sub(" ", normalized).strip().casefold()

        return PreprocessedText(original, normalized, self.detect_language(normalized))

    def build_tender_document(
        self, *, title: str | None, description: str | None, item_texts: Iterable[str | None] = ()
    ) -> PreprocessedText:
        sections = [
            f"titulo: {title}" if title else "",
            f"descripcion: {description}" if description else "",
            *[f"item: {item}" for item in item_texts if item],
        ]
        return self.preprocess("\n".join(section for section in sections if section))

    @staticmethod
    def detect_language(text: str) -> str:
        if not text:
            return "und"
        words = re.findall(r"[a-záéíóúñü]+", text)
        if not words:
            return "und"
        matches = sum(1 for word in words if word in _SPANISH_MARKERS)
        # Short texts (titles) only get one shot at a marker; longer texts need
        # a meaningful fraction so a couple of incidental words don't tip it.
        if len(words) <= 5:
            return "es" if matches >= 1 else "und"
        return "es" if matches / len(words) >= 0.15 else "und"


def _expand_abbreviations(text: str) -> str:
    return _NUMERO_PATTERN.sub("numero ", text)


def _normalize_units(text: str) -> str:
    text = _UNIDAD_PATTERN.sub(lambda m: f"{m.group(1)} unidad", text)
    for pattern, replacement in _SIMPLE_UNIT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
