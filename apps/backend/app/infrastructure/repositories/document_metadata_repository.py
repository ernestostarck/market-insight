from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities.document import DocumentMetadataRecord
from app.domain.ports.document_repository import DocumentMetadataRepository
from app.models.document_metadata import DocumentMetadata


class SqlAlchemyDocumentMetadataRepository(DocumentMetadataRepository):
    """SQLAlchemy repository for document metadata records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: DocumentMetadataRecord) -> DocumentMetadataRecord:
        model = DocumentMetadata(
            bucket=entity.bucket,
            object_name=entity.object_name,
            uri=entity.uri,
            is_public=entity.is_public,
            content_type=entity.content_type,
            size_bytes=entity.size_bytes,
            checksum_sha256=entity.checksum_sha256,
            original_filename=entity.original_filename,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_record(model)

    def get_by_object_name(self, object_name: str) -> DocumentMetadataRecord | None:
        model = self._session.scalar(
            select(DocumentMetadata).where(DocumentMetadata.object_name == object_name)
        )
        return self._to_record(model) if model is not None else None

    def list(self) -> Iterable[DocumentMetadataRecord]:
        models = self._session.scalars(
            select(DocumentMetadata).order_by(DocumentMetadata.created_at.desc())
        ).all()
        return [self._to_record(model) for model in models]

    def remove(self, object_name: str) -> None:
        self._session.execute(
            delete(DocumentMetadata).where(DocumentMetadata.object_name == object_name)
        )
        self._session.commit()

    @staticmethod
    def _to_record(model: DocumentMetadata | None) -> DocumentMetadataRecord:
        if model is None:
            raise ValueError("Document metadata model is required")
        return DocumentMetadataRecord(
            id=model.id,
            bucket=model.bucket,
            object_name=model.object_name,
            uri=model.uri,
            is_public=model.is_public,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            checksum_sha256=model.checksum_sha256,
            original_filename=model.original_filename,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
