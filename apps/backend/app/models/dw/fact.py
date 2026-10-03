from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FactLicitacion(Base):
    """Hecho de actividad de licitación."""

    __tablename__ = "fact_licitacion"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    licitacion_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    fecha_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_fecha.fecha_key"), nullable=True, index=True
    )
    organismo_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_organismo.organismo_key"), nullable=True, index=True
    )
    categoria_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_categoria.categoria_key"), nullable=True, index=True
    )
    tipo_licitacion_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_tipo_licitacion.tipo_key"), nullable=True, index=True
    )
    estado_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_estado_licitacion.estado_key"), nullable=True, index=True
    )
    monto_estimado: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cantidad_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cantidad_ofertas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_adjudicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    es_desierta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fuente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FactOferta(Base):
    """Hecho de participación competitiva (oferta)."""

    __tablename__ = "fact_oferta"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    oferta_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    fecha_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_fecha.fecha_key"), nullable=True, index=True
    )
    licitacion_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.fact_licitacion.id"), nullable=True, index=True
    )
    proveedor_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_proveedor.proveedor_key"), nullable=True, index=True
    )
    categoria_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_categoria.categoria_key"), nullable=True, index=True
    )
    monto_oferta: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    posicion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_adjudicada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fuente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FactAdjudicacion(Base):
    """Hecho de adjudicación (resultado)."""

    __tablename__ = "fact_adjudicacion"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    adjudicacion_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    fecha_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_fecha.fecha_key"), nullable=True, index=True
    )
    licitacion_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.fact_licitacion.id"), nullable=True, index=True
    )
    proveedor_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_proveedor.proveedor_key"), nullable=True, index=True
    )
    organismo_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_organismo.organismo_key"), nullable=True, index=True
    )
    categoria_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_categoria.categoria_key"), nullable=True, index=True
    )
    monto_adjudicado: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    monto_estimado: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    ratio_adjudicacion: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )
    cantidad_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cantidad_ofertas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FactOrdenCompra(Base):
    """Hecho de materialización de compra (orden de compra)."""

    __tablename__ = "fact_orden_compra"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    orden_compra_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    fecha_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_fecha.fecha_key"), nullable=True, index=True
    )
    organismo_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_organismo.organismo_key"), nullable=True, index=True
    )
    proveedor_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_proveedor.proveedor_key"), nullable=True, index=True
    )
    categoria_key: Mapped[int | None] = mapped_column(
        ForeignKey("dw.dim_categoria.categoria_key"), nullable=True, index=True
    )
    monto_neto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_iva: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    monto_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    cantidad_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
