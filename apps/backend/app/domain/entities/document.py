from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class DocumentMetadataRecord:
    id: int | None
    bucket: str
    object_name: str
    uri: str
    is_public: bool
    content_type: str
    size_bytes: int
    checksum_sha256: str
    original_filename: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
