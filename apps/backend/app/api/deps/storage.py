from app.api.deps.container import get_minio_client, get_object_storage
from app.domain.ports.object_storage import ObjectStoragePort
from app.infrastructure.storage.minio_storage import MinioObjectStorage

__all__ = [
    "MinioObjectStorage",
    "ObjectStoragePort",
    "get_minio_client",
    "get_object_storage",
]
