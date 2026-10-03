import hashlib
from dataclasses import dataclass
from urllib.parse import quote

from app.core.settings import Settings
from app.domain.entities.document import DocumentMetadataRecord
from app.domain.ports.document_repository import DocumentMetadataRepository
from app.domain.ports.object_storage import ObjectStoragePort


@dataclass(slots=True)
class StoredDocument:
    bucket: str
    object_name: str
    uri: str
    is_public: bool


@dataclass(slots=True)
class DocumentDownloadLink:
    bucket: str
    object_name: str
    download_url: str
    is_public: bool


class DocumentStorageUseCase:
    """Store and retrieve documents from the object storage backend."""

    def __init__(
        self,
        storage: ObjectStoragePort,
        metadata_repository: DocumentMetadataRepository,
    ) -> None:
        self._storage = storage
        self._metadata_repository = metadata_repository

    def store_document(
        self,
        settings: Settings,
        object_name: str,
        data: bytes,
        content_type: str,
        is_public: bool = False,
        original_filename: str | None = None,
    ) -> StoredDocument:
        bucket = (
            settings.minio_bucket_public_documents
            if is_public
            else settings.minio_bucket_private_documents
        )
        self._storage.ensure_bucket(bucket)
        uri = self._storage.upload(bucket, object_name, data, content_type)
        self._metadata_repository.add(
            DocumentMetadataRecord(
                id=None,
                bucket=bucket,
                object_name=object_name,
                uri=uri,
                is_public=is_public,
                content_type=content_type,
                size_bytes=len(data),
                checksum_sha256=hashlib.sha256(data).hexdigest(),
                original_filename=original_filename,
            )
        )
        return StoredDocument(
            bucket=bucket,
            object_name=object_name,
            uri=uri,
            is_public=is_public,
        )

    def fetch_document(self, settings: Settings, object_name: str) -> bytes:
        metadata = self._metadata_repository.get_by_object_name(object_name)
        bucket = (
            metadata.bucket
            if metadata is not None
            else settings.minio_bucket_private_documents
        )
        return self._storage.download(bucket, object_name)

    def get_download_link(
        self,
        settings: Settings,
        object_name: str,
        expires_in_seconds: int = 3600,
    ) -> DocumentDownloadLink:
        metadata = self._metadata_repository.get_by_object_name(object_name)
        if metadata is None:
            bucket = settings.minio_bucket_private_documents
            is_public = False
        else:
            bucket = metadata.bucket
            is_public = metadata.is_public

        if is_public:
            download_url = self._build_public_url(settings, bucket, object_name)
        else:
            download_url = self._storage.presign_download(
                bucket, object_name, expires_in_seconds
            )

        return DocumentDownloadLink(
            bucket=bucket,
            object_name=object_name,
            download_url=download_url,
            is_public=is_public,
        )

    @staticmethod
    def _build_public_url(settings: Settings, bucket: str, object_name: str) -> str:
        endpoint = settings.minio_endpoint
        scheme = "https" if endpoint.startswith("https://") else "http"
        host = endpoint.removeprefix("http://").removeprefix("https://")
        return f"{scheme}://{host}/{quote(bucket)}/{quote(object_name, safe='/')}"
