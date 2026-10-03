from collections.abc import Sequence
from typing import Protocol


class ObjectStoragePort(Protocol):
    """Contract for object storage providers."""

    def upload(
        self, bucket: str, object_name: str, data: bytes, content_type: str
    ) -> str:
        """Upload an object and return its storage URI."""

    def download(self, bucket: str, object_name: str) -> bytes:
        """Download an object as raw bytes."""

    def delete(self, bucket: str, object_name: str) -> None:
        """Delete an object from storage."""

    def presign_download(
        self, bucket: str, object_name: str, expires_in_seconds: int
    ) -> str:
        """Create a signed download URL for an object."""

    def ensure_bucket(self, bucket: str) -> None:
        """Create the bucket if it does not exist."""

    def list_buckets(self) -> Sequence[str]:
        """List available buckets."""
