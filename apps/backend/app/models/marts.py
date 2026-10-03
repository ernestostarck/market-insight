from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketMonthly(Base):
    __tablename__ = "mv_market_monthly"
    __table_args__ = {"schema": "analytics"}

    mes: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    total_licitaciones: Mapped[int] = mapped_column(BigInteger)
    total_adjudicaciones: Mapped[int] = mapped_column(BigInteger)
    monto_total_adjudicado: Mapped[Decimal] = mapped_column(Numeric)


class SupplierPerformance(Base):
    __tablename__ = "v_supplier_performance"
    __table_args__ = {"schema": "suppliers_mart"}

    razon_social: Mapped[str] = mapped_column(String, primary_key=True)
    rut: Mapped[str] = mapped_column(String)
    total_adjudicaciones: Mapped[int] = mapped_column(BigInteger)
    monto_total_adjudicado: Mapped[Decimal] = mapped_column(Numeric)
    ratio_adjudicacion_promedio: Mapped[Decimal] = mapped_column(Numeric)
    ultima_adjudicacion: Mapped[datetime.date] = mapped_column(Date)


class CategorySpending(Base):
    __tablename__ = "v_category_spending"
    __table_args__ = {"schema": "categories_mart"}

    categoria: Mapped[str] = mapped_column(String, primary_key=True)
    codigo_categoria: Mapped[str] = mapped_column(String)
    gasto_total_oc: Mapped[Decimal] = mapped_column(Numeric)
    numero_ordenes_compra: Mapped[int] = mapped_column(BigInteger)
    gasto_promedio_oc: Mapped[Decimal] = mapped_column(Numeric)


class DisabilityContract(Base):
    __tablename__ = "v_disability_contracts"
    __table_args__ = {"schema": "disability_market_mart"}

    licitacion_id: Mapped[str] = mapped_column(String, primary_key=True)
    nombre: Mapped[str] = mapped_column(String)
    descripcion: Mapped[str] = mapped_column(String)
    monto_adjudicado: Mapped[Decimal] = mapped_column(Numeric)
    proveedor: Mapped[str] = mapped_column(String)
    organismo: Mapped[str] = mapped_column(String)
    periodo: Mapped[datetime.date] = mapped_column(Date)


class DQMissingKeys(Base):
    __tablename__ = "v_facts_missing_keys"
    __table_args__ = {"schema": "dq_views"}

    fact_table: Mapped[str] = mapped_column(String, primary_key=True)
    missing_count: Mapped[int] = mapped_column(BigInteger)


class LineageMartToDW(Base):
    __tablename__ = "v_marts_to_dw"
    __table_args__ = {"schema": "lineage_views"}

    mart_view: Mapped[str] = mapped_column(String, primary_key=True)
    dw_dependencies: Mapped[str] = mapped_column(String)
