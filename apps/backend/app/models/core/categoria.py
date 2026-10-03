from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Categoria(Base):
    """Categoría de bienes/servicios — modelo canónico core."""

    __tablename__ = "categoria"
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
    categoria_padre: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nivel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    natural_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
