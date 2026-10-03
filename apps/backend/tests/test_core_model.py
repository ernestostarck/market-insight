from __future__ import annotations

from app.db.base import Base
from app.models import (
    Adjudicacion,
    Categoria,
    Documento,
    Licitacion,
    LicitacionItem,
    Oferta,
    OrdenCompra,
    OrdenCompraItem,
    Organismo,
    Producto,
    Proveedor,
)


def _table(name: str):
    return Base.metadata.tables[f"core.{name}"]


def test_core_schema_tables_registered() -> None:
    expected = {
        "organismo",
        "proveedor",
        "licitacion",
        "licitacion_item",
        "oferta",
        "adjudicacion",
        "orden_compra",
        "orden_compra_item",
        "categoria",
        "producto",
        "documento",
    }
    actual = {name for name in Base.metadata.tables if name.startswith("core.")}
    for table in expected:
        assert f"core.{table}" in actual, f"missing core table {table}"


def test_organismo_has_source_traceability_columns() -> None:
    cols = _table("organismo").columns
    assert "source_id" in cols
    assert "source_system" in cols
    assert "natural_key" in cols
    assert "payload_hash" in cols
    assert cols["natural_key"].unique


def test_proveedor_has_source_traceability_columns() -> None:
    cols = _table("proveedor").columns
    assert "source_id" in cols
    assert "source_system" in cols
    assert "rut" in cols
    assert "natural_key" in cols


def test_licitacion_relationships_and_amounts() -> None:
    cols = _table("licitacion").columns
    assert "organismo_id" in cols
    assert "categoria_id" in cols
    assert "monto_estimado" in cols
    assert "fecha_publicacion" in cols
    assert "fecha_cierre" in cols
    assert "es_adjudicada" in cols
    assert "es_desierta" in cols
    # moneda defaults to CLP
    assert "moneda" in cols


def test_licitacion_item_has_amount_columns() -> None:
    cols = _table("licitacion_item").columns
    assert "licitacion_id" in cols
    assert "producto_id" in cols
    assert "cantidad" in cols
    assert "precio_unitario" in cols
    assert "monto_total" in cols


def test_oferta_has_competition_columns() -> None:
    cols = _table("oferta").columns
    assert "licitacion_id" in cols
    assert "proveedor_id" in cols
    assert "monto" in cols
    assert "posicion" in cols
    assert "es_adjudicada" in cols


def test_adjudicacion_has_award_columns() -> None:
    cols = _table("adjudicacion").columns
    assert "licitacion_id" in cols
    assert "proveedor_id" in cols
    assert "organismo_id" in cols
    assert "monto_adjudicado" in cols
    assert "ratio_adjudicacion" in cols
    assert "quality_flags" in cols


def test_orden_compra_has_money_columns() -> None:
    cols = _table("orden_compra").columns
    assert "licitacion_id" in cols
    assert "adjudicacion_id" in cols
    assert "organismo_id" in cols
    assert "proveedor_id" in cols
    assert "monto_neto" in cols
    assert "monto_iva" in cols
    assert "monto_total" in cols


def test_orden_compra_item_has_amount_columns() -> None:
    cols = _table("orden_compra_item").columns
    assert "orden_compra_id" in cols
    assert "producto_id" in cols
    assert "cantidad" in cols
    assert "monto_total" in cols


def test_documento_has_licitacion_relation() -> None:
    cols = _table("documento").columns
    assert "licitacion_id" in cols
    assert "tipo" in cols
    assert "checksum_sha256" in cols


def test_models_exported() -> None:
    assert Organismo.__tablename__ == "organismo"
    assert Proveedor.__tablename__ == "proveedor"
    assert Licitacion.__tablename__ == "licitacion"
    assert LicitacionItem.__tablename__ == "licitacion_item"
    assert Oferta.__tablename__ == "oferta"
    assert Adjudicacion.__tablename__ == "adjudicacion"
    assert OrdenCompra.__tablename__ == "orden_compra"
    assert OrdenCompraItem.__tablename__ == "orden_compra_item"
    assert Categoria.__tablename__ == "categoria"
    assert Producto.__tablename__ == "producto"
    assert Documento.__tablename__ == "documento"
