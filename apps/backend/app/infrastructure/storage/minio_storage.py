from __future__ import annotations

from datetime import timedelta
from io import BytesIO

from minio import Minio

from app.domain.ports.object_storage import ObjectStoragePort


class MinioObjectStorage(ObjectStoragePort):
    """MinIO-backed object storage implementation."""

    def __init__(self, client: Minio) -> None:
        self._client = client

    def upload(
        self, bucket: str, object_name: str, data: bytes, content_type: str
    ) -> str:
        self._client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"s3://{bucket}/{object_name}"

    def download(self, bucket: str, object_name: str) -> bytes:
        response = self._client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, bucket: str, object_name: str) -> None:
        self._client.remove_object(bucket, object_name)

    def presign_download(
        self, bucket: str, object_name: str, expires_in_seconds: int
    ) -> str:
        return self._client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_in_seconds),
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def list_buckets(self) -> list[str]:
        return [bucket.name for bucket in self._client.list_buckets()]
