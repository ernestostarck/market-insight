from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core._types import jsonb_type


class Organismo(Base):
    """Organismo comprador (agencia) del Mercado Público — modelo canónico core."""

    __tablename__ = "organismo"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    codigo: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    tipo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(256), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comuna: Mapped[str | None] = mapped_column(String(128), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    natural_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(jsonb_type(), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
