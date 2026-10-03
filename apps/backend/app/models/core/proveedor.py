from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core._types import jsonb_type


class Proveedor(Base):
    """Proveedor que participa en Mercado Público — modelo canónico core."""

    __tablename__ = "proveedor"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    rut: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    razon_social: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_fantasia: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    tipo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    categoria_economica: Mapped[str | None] = mapped_column(String(256), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    comuna: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
