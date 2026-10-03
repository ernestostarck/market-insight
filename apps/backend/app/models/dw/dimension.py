from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DimFecha(Base):
    """Dimensión de fecha (calendario) para análisis temporal."""

    __tablename__ = "dim_fecha"
    __table_args__ = {"schema": "dw"}

    fecha_key: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    dia: Mapped[int] = mapped_column(Integer, nullable=False)
    trimestre: Mapped[int] = mapped_column(Integer, nullable=False)
    semana: Mapped[int] = mapped_column(Integer, nullable=False)
    nombre_mes: Mapped[str] = mapped_column(String(32), nullable=True)
    nombre_dia: Mapped[str] = mapped_column(String(32), nullable=True)
    es_fin_de_semana: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    es_feriado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anio_mes: Mapped[str] = mapped_column(String(7), nullable=False, index=True)


class DimOrganismo(Base):
    """Dimensión de organismo comprador (SCD Type 2 habilitado)."""

    __tablename__ = "dim_organismo"
    __table_args__ = {"schema": "dw"}

    organismo_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    codigo: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    natural_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    tipo: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(256), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comuna: Mapped[str | None] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )


class DimProveedor(Base):
    """Dimensión de proveedor (SCD Type 2 habilitado)."""

    __tablename__ = "dim_proveedor"
    __table_args__ = {"schema": "dw"}

    proveedor_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    rut: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
    razon_social: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_fantasia: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    natural_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    tipo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comuna: Mapped[str | None] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )


class DimCategoria(Base):
    """Dimensión de categoría de bienes/servicios."""

    __tablename__ = "dim_categoria"
    __table_args__ = {"schema": "dw"}

    categoria_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    codigo: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    categoria_padre: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nivel: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DimProducto(Base):
    """Dimensión de producto."""

    __tablename__ = "dim_producto"
    __table_args__ = {"schema": "dw"}

    producto_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    codigo: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(512), nullable=True)
    nombre_normalizado: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    categoria_key: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    unidad: Mapped[str | None] = mapped_column(String(64), nullable=True)


class DimUbicacion(Base):
    """Dimensión de ubicación geográfica."""

    __tablename__ = "dim_ubicacion"
    __table_args__ = {"schema": "dw"}

    ubicacion_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    comuna: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provincia: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)


class DimEstadoLicitacion(Base):
    """Dimensión de estado de licitación."""

    __tablename__ = "dim_estado_licitacion"
    __table_args__ = {"schema": "dw"}

    estado_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    nombre: Mapped[str | None] = mapped_column(String(256), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(512), nullable=True)


class DimTipoLicitacion(Base):
    """Dimensión de tipo de licitación."""

    __tablename__ = "dim_tipo_licitacion"
    __table_args__ = {"schema": "dw"}

    tipo_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    nombre: Mapped[str | None] = mapped_column(String(256), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String(512), nullable=True)
