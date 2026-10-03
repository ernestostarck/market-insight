from collections.abc import Iterable
from typing import Protocol

from app.domain.entities.document import DocumentMetadataRecord


class DocumentMetadataRepository(Protocol):
    """Contract for persisted document metadata."""

    def add(self, entity: DocumentMetadataRecord) -> DocumentMetadataRecord:
        """Persist a document metadata record."""

    def get_by_object_name(self, object_name: str) -> DocumentMetadataRecord | None:
        """Load a metadata record by object name."""

    def list(self) -> Iterable[DocumentMetadataRecord]:
        """Return all metadata records."""

    def remove(self, object_name: str) -> None:
        """Delete a metadata record by object name."""
