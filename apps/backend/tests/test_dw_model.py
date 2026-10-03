from __future__ import annotations

from app.db.base import Base
from app.models import (
    DimCategoria,
    DimEstadoLicitacion,
    DimFecha,
    DimOrganismo,
    DimProducto,
    DimProveedor,
    DimTipoLicitacion,
    DimUbicacion,
    FactAdjudicacion,
    FactLicitacion,
    FactOferta,
    FactOrdenCompra,
)


def _table(name: str):
    return Base.metadata.tables[f"dw.{name}"]


def test_dw_schema_tables_registered() -> None:
    expected = {
        "dim_fecha",
        "dim_organismo",
        "dim_proveedor",
        "dim_categoria",
        "dim_producto",
        "dim_ubicacion",
        "dim_estado_licitacion",
        "dim_tipo_licitacion",
        "fact_licitacion",
        "fact_oferta",
        "fact_adjudicacion",
        "fact_orden_compra",
    }
    actual = {name for name in Base.metadata.tables if name.startswith("dw.")}
    for table in expected:
        assert f"dw.{table}" in actual, f"missing dw table {table}"


def test_dim_fecha_has_calendar_columns() -> None:
    cols = _table("dim_fecha").columns
    for col in (
        "fecha_key",
        "fecha",
        "anio",
        "mes",
        "dia",
        "trimestre",
        "semana",
        "anio_mes",
    ):
        assert col in cols, f"missing dim_fecha.{col}"
    assert cols["fecha"].unique


def test_dim_organismo_has_scd2_columns() -> None:
    cols = _table("dim_organismo").columns
    for col in ("valid_from", "valid_to", "is_current", "source_id", "natural_key"):
        assert col in cols, f"missing dim_organismo.{col}"


def test_dim_proveedor_has_scd2_columns() -> None:
    cols = _table("dim_proveedor").columns
    for col in ("valid_from", "valid_to", "is_current", "rut", "natural_key"):
        assert col in cols, f"missing dim_proveedor.{col}"


def test_fact_licitacion_has_measure_columns() -> None:
    cols = _table("fact_licitacion").columns
    for col in (
        "fecha_key",
        "organismo_key",
        "categoria_key",
        "tipo_licitacion_key",
        "estado_key",
        "monto_estimado",
        "cantidad_items",
        "cantidad_ofertas",
    ):
        assert col in cols, f"missing fact_licitacion.{col}"


def test_fact_oferta_has_competition_measure_columns() -> None:
    cols = _table("fact_oferta").columns
    for col in (
        "fecha_key",
        "proveedor_key",
        "monto_oferta",
        "posicion",
        "es_adjudicada",
    ):
        assert col in cols


def test_fact_adjudicacion_has_award_measure_columns() -> None:
    cols = _table("fact_adjudicacion").columns
    for col in (
        "fecha_key",
        "proveedor_key",
        "organismo_key",
        "monto_adjudicado",
        "monto_estimado",
        "ratio_adjudicacion",
    ):
        assert col in cols


def test_fact_orden_compra_has_money_measure_columns() -> None:
    cols = _table("fact_orden_compra").columns
    for col in (
        "fecha_key",
        "organismo_key",
        "proveedor_key",
        "monto_neto",
        "monto_iva",
        "monto_total",
    ):
        assert col in cols


def test_dim_tables_have_integer_surrogate_keys() -> None:
    for table in (
        "dim_fecha",
        "dim_organismo",
        "dim_proveedor",
        "dim_categoria",
        "dim_producto",
        "dim_ubicacion",
        "dim_estado_licitacion",
        "dim_tipo_licitacion",
    ):
        table_obj = _table(table)
        pk = list(table_obj.primary_key.columns)
        assert len(pk) == 1, f"{table} must have single-column PK"
        assert pk[0].type.python_type is int, f"{table} PK must be integer"


def test_dw_models_exported() -> None:
    assert DimFecha.__tablename__ == "dim_fecha"
    assert DimOrganismo.__tablename__ == "dim_organismo"
    assert DimProveedor.__tablename__ == "dim_proveedor"
    assert DimCategoria.__tablename__ == "dim_categoria"
    assert DimProducto.__tablename__ == "dim_producto"
    assert DimUbicacion.__tablename__ == "dim_ubicacion"
    assert DimEstadoLicitacion.__tablename__ == "dim_estado_licitacion"
    assert DimTipoLicitacion.__tablename__ == "dim_tipo_licitacion"
    assert FactLicitacion.__tablename__ == "fact_licitacion"
    assert FactOferta.__tablename__ == "fact_oferta"
    assert FactAdjudicacion.__tablename__ == "fact_adjudicacion"
    assert FactOrdenCompra.__tablename__ == "fact_orden_compra"
