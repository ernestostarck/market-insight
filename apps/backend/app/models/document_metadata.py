from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"
    __table_args__ = {"schema": "documents"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bucket: Mapped[str] = mapped_column(String(128), index=True)
    object_name: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    uri: Mapped[str] = mapped_column(String(1024))
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
