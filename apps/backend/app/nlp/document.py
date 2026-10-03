"""Tender document consolidation: wraps `TextPreprocessor.build_tender_document`
output into the persistable Document/Chunk structure.

See docs/07-ai/document-processing.md for which textual sources are active
today (nombre, descripcion) versus blocked (items, especificaciones tecnicas,
observaciones, documentos asociados) and why.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Iterator

from app.nlp.preprocessing import PreprocessedText

_SENTENCE_END = re.compile(r"[.!?]+\s+")
_WHITESPACE_RUN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    sequence: int
    text: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class TenderDocument:
    licitacion_id: int
    raw_text: str
    normalized_text: str
    language: str
    content_hash: str
    chunks: tuple[DocumentChunk, ...]


class TextChunker:
    """Split normalized text into chunks without cutting mid-word or mid-sentence.

    Today's sources (nombre + descripcion) are short and produce a single
    chunk. The multi-chunk path exists so that when longer blocked sources
    (documentos asociados) are unblocked, the chunking strategy does not need
    to be redesigned — only fed more text.
    """

    def __init__(self, max_chars: int = 1000) -> None:
        self._max_chars = max_chars

    def split(self, text: str) -> tuple[DocumentChunk, ...]:
        if not text:
            return ()
        if len(text) <= self._max_chars:
            return (DocumentChunk(sequence=0, text=text, start_offset=0, end_offset=len(text)),)
        return _merge_spans(text, _unit_spans(text, self._max_chars), self._max_chars)


def build_document(
    licitacion_id: int, preprocessed: PreprocessedText, *, chunker: TextChunker | None = None,
) -> TenderDocument:
    chunker = chunker or TextChunker()
    chunks = chunker.split(preprocessed.normalized_text)
    return TenderDocument(
        licitacion_id=licitacion_id,
        raw_text=preprocessed.original_text,
        normalized_text=preprocessed.normalized_text,
        language=preprocessed.language,
        content_hash=_content_hash(preprocessed.normalized_text),
        chunks=chunks,
    )


def _content_hash(normalized_text: str) -> str:
    return sha256(normalized_text.encode("utf-8")).hexdigest()


def _iter_sentences(text: str) -> Iterator[tuple[int, int]]:
    """Contiguous spans covering the whole text, split after '.', '!' or '?'
    plus trailing whitespace. Falls back to one span if there is no
    punctuation at all."""
    start = 0
    for match in _SENTENCE_END.finditer(text):
        end = match.end()
        yield (start, end)
        start = end
    if start < len(text):
        yield (start, len(text))


def _iter_words(text: str, start: int, end: int) -> Iterator[tuple[int, int]]:
    """Contiguous spans covering [start, end): words and the whitespace runs
    between them, so re-joining the spans reproduces the original slice."""
    pos = start
    for match in _WHITESPACE_RUN.finditer(text, start, end):
        if match.start() > pos:
            yield (pos, match.start())
        yield (match.start(), match.end())
        pos = match.end()
    if pos < end:
        yield (pos, end)


def _unit_spans(text: str, max_chars: int) -> Iterator[tuple[int, int]]:
    """Contiguous spans covering the whole text: sentences, or — for a single
    sentence longer than max_chars — its word-level sub-spans."""
    for start, end in _iter_sentences(text):
        if end - start > max_chars:
            yield from _iter_words(text, start, end)
        else:
            yield (start, end)


def _merge_spans(text: str, spans: Iterable[tuple[int, int]], max_chars: int) -> tuple[DocumentChunk, ...]:
    """Greedily merge contiguous unit spans into chunks up to max_chars,
    never splitting a unit — even a single oversized unit becomes its own
    chunk rather than being cut mid-word."""
    chunks: list[DocumentChunk] = []
    buf_start: int | None = None
    buf_end: int | None = None
    for start, end in spans:
        if buf_start is None:
            buf_start, buf_end = start, end
        elif end - buf_start <= max_chars:
            buf_end = end
        else:
            assert buf_end is not None
            chunks.append(DocumentChunk(len(chunks), text[buf_start:buf_end], buf_start, buf_end))
            buf_start, buf_end = start, end
    if buf_start is not None:
        assert buf_end is not None
        chunks.append(DocumentChunk(len(chunks), text[buf_start:buf_end], buf_start, buf_end))
    return tuple(chunks)
