from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core._types import jsonb_type


class Licitacion(Base):
    """Licitación publicada en Mercado Público — modelo canónico core."""

    __tablename__ = "licitacion"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    codigo: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tipo: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    organismo_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.organismo.id"), nullable=True, index=True
    )
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.categoria.id"), nullable=True, index=True
    )
    fecha_publicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    fecha_adjudicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    monto_estimado: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(8), nullable=True, default="CLP")
    es_desierta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    es_adjudicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class LicitacionItem(Base):
    """Ítem dentro de una licitación — modelo canónico core."""

    __tablename__ = "licitacion_item"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    licitacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.licitacion.id"), nullable=True, index=True
    )
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.producto.id"), nullable=True, index=True
    )
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.categoria.id"), nullable=True, index=True
    )
    codigo: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    cantidad: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    unidad: Mapped[str | None] = mapped_column(String(64), nullable=True)
    precio_unitario: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_total: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(8), nullable=True, default="CLP")
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


class Oferta(Base):
    """Oferta presentada por un proveedor a una licitación — modelo canónico core."""

    __tablename__ = "oferta"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    licitacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.licitacion.id"), nullable=True, index=True
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.proveedor.id"), nullable=True, index=True
    )
    monto: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(8), nullable=True, default="CLP")
    fecha: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    posicion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_adjudicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class Adjudicacion(Base):
    """Adjudicación de una licitación a un proveedor — modelo canónico core."""

    __tablename__ = "adjudicacion"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    licitacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.licitacion.id"), nullable=True, index=True
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.proveedor.id"), nullable=True, index=True
    )
    organismo_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.organismo.id"), nullable=True, index=True
    )
    oferta_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.oferta.id"), nullable=True, index=True
    )
    monto_adjudicado: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    monto_estimado: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    ratio_adjudicacion: Mapped[float | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    cantidad_ofertas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha_adjudicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quality_flags: Mapped[list | None] = mapped_column(jsonb_type(), nullable=True)
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
