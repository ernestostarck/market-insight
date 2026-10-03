from functools import lru_cache

from fastapi import Depends
from minio import Minio
from sqlalchemy.orm import Session

from app.api.deps.settings import get_settings
from app.application.use_cases.adjudicacion_analytics import (
    AdjudicacionAnalyticsUseCase,
)
from app.application.use_cases.document_storage import DocumentStorageUseCase
from app.application.use_cases.system_status import SystemStatusUseCase
from app.db.session import get_db
from app.infrastructure.repositories.adjudicacion_analytics_repository import (
    SqlAlchemyAdjudicacionAnalyticsRepository,
)
from app.infrastructure.repositories.document_metadata_repository import (
    SqlAlchemyDocumentMetadataRepository,
)
from app.infrastructure.storage.minio_storage import MinioObjectStorage
from app.integrations.chilecompra.sdk import ChileCompraClient


@lru_cache
def get_minio_client() -> Minio:
    """Return a singleton MinIO client."""
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


@lru_cache
def get_system_status_use_case() -> SystemStatusUseCase:
    """Return the system status use case singleton."""
    return SystemStatusUseCase()


def get_document_metadata_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyDocumentMetadataRepository:
    """Return the PostgreSQL-backed document metadata repository."""
    return SqlAlchemyDocumentMetadataRepository(db)


def get_document_storage_use_case(
    metadata_repository: SqlAlchemyDocumentMetadataRepository = Depends(
        get_document_metadata_repository
    ),
) -> DocumentStorageUseCase:
    """Return the document storage use case."""
    return DocumentStorageUseCase(get_object_storage(), metadata_repository)


@lru_cache
def get_chilecompra_client() -> ChileCompraClient:
    """Return the ChileCompra SDK facade singleton."""
    return ChileCompraClient.from_settings()


def get_adjudicacion_analytics_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyAdjudicacionAnalyticsRepository:
    """Return repository for analytics snapshots in PostgreSQL."""
    return SqlAlchemyAdjudicacionAnalyticsRepository(db)


def get_adjudicacion_analytics_use_case(
    repository: SqlAlchemyAdjudicacionAnalyticsRepository = Depends(
        get_adjudicacion_analytics_repository
    ),
) -> AdjudicacionAnalyticsUseCase:
    """Return analytics persistence use case for adjudicaciones."""
    return AdjudicacionAnalyticsUseCase(repository, get_chilecompra_client())


def get_object_storage() -> MinioObjectStorage:
    """Return the object storage adapter backed by MinIO."""
    return MinioObjectStorage(get_minio_client())
