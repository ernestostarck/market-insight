from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core._types import jsonb_type


class OrdenCompra(Base):
    """Orden de compra derivada de una licitación/adjudicación — modelo canónico core."""

    __tablename__ = "orden_compra"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    source_system: Mapped[str] = mapped_column(
        String(64), nullable=False, default="mercado_publico"
    )
    codigo: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    licitacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.licitacion.id"), nullable=True, index=True
    )
    adjudicacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.adjudicacion.id"), nullable=True, index=True
    )
    organismo_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.organismo.id"), nullable=True, index=True
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.proveedor.id"), nullable=True, index=True
    )
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fecha_creacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    fecha_emision: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    monto_neto: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_iva: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_total: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[str | None] = mapped_column(String(8), nullable=True, default="CLP")
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


class OrdenCompraItem(Base):
    """Ítem dentro de una orden de compra — modelo canónico core."""

    __tablename__ = "orden_compra_item"
    __table_args__ = {"schema": "core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    orden_compra_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.orden_compra.id"), nullable=True, index=True
    )
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("core.producto.id"), nullable=True, index=True
    )
    codigo: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(1024), nullable=True)
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
