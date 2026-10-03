"""Preprocessing application service (Fase 6.18)."""

from __future__ import annotations

import hashlib
import uuid

from app.models.knowledge import Chunk, Document
from app.nlp.document import TenderDocument, build_document
from app.nlp.preprocessing import PreprocessedText, TextPreprocessor
from app.repositories.knowledge import ChunkRepository, DocumentRepository


class PreprocessingService:
    def __init__(
        self,
        preprocessor: TextPreprocessor | None = None,
        document_repository: DocumentRepository | None = None,
        chunk_repository: ChunkRepository | None = None,
    ) -> None:
        self._preprocessor = preprocessor or TextPreprocessor()
        self._document_repo = document_repository
        self._chunk_repo = chunk_repository

    def preprocess(self, text: str) -> PreprocessedText:
        return self._preprocessor.preprocess(text)

    def build_tender_document(
        self, title: str, description: str | None, item_texts: list[str]
    ) -> PreprocessedText:
        return self._preprocessor.build_tender_document(
            title=title, description=description, item_texts=item_texts
        )

    def build_consolidated_document(
        self, licitacion_id: int, title: str, description: str | None, item_texts: list[str]
    ) -> TenderDocument:
        preprocessed = self.build_tender_document(
            title=title, description=description, item_texts=item_texts
        )
        return build_document(licitacion_id=licitacion_id, preprocessed=preprocessed)

    async def process_and_store_tender(
        self, licitacion_id: int, title: str, description: str | None, item_texts: list[str]
    ) -> Document:
        doc = self.build_consolidated_document(
            licitacion_id=licitacion_id, title=title, description=description, item_texts=item_texts
        )
        content_hash = doc.content_hash

        if self._document_repo is not None:
            existing = await self._document_repo.get_by_content_hash(licitacion_id, content_hash)
            if existing is not None:
                return existing

        document_id = uuid.uuid4()
        db_doc = Document(
            id=document_id,
            licitacion_id=licitacion_id,
            raw_text=doc.raw_text,
            normalized_text=doc.normalized_text,
            language=doc.language,
            content_hash=content_hash,
        )

        if self._document_repo is not None:
            db_doc = await self._document_repo.create(db_doc)

        if self._chunk_repo is not None:
            chunks = [
                Chunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    sequence=c.sequence,
                    text=c.text,
                    start_offset=c.start_offset,
                    end_offset=c.end_offset,
                )
                for c in doc.chunks
            ]
            if chunks:
                await self._chunk_repo.create_many(chunks)

        return db_doc
