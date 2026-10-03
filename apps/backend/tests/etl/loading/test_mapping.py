from __future__ import annotations

import pytest
from app.etl.loading.mapping import (
    has_table,
    project_columns,
    table_for,
    table_name,
)
from app.etl.models import StoredRawRecord  # noqa: F401  (kept for fixtures parity)


@pytest.mark.parametrize(
    "entity,expected_schema,expected_table",
    [
        ("licitacion", "procurement", "licitaciones"),
        ("orden_compra", "procurement", "ordenes_compra"),
        ("empresa", "procurement", "proveedores"),
        ("contrato", "procurement", "contratos"),
        ("convenio_marco", "procurement", "convenios_marco"),
        ("adjudicacion", "procurement", "adjudicaciones"),
    ],
)
def test_table_for_maps_known_entities(entity, expected_schema, expected_table) -> None:
    mapping = table_for(entity)

    assert mapping.schema == expected_schema
    assert mapping.table == expected_table


def test_table_for_unknown_entity_raises() -> None:
    with pytest.raises(KeyError):
        table_for("desconocido")


@pytest.mark.parametrize("entity", ["licitacion", "empresa", "adjudicacion"])
def test_has_table_for_known_entities(entity) -> None:
    assert has_table(entity) is True


def test_has_table_for_unknown_entity() -> None:
    assert has_table("unknown") is False


@pytest.mark.parametrize(
    "entity,expected",
    [
        ("licitacion", "procurement.licitaciones"),
        ("adjudicacion", "procurement.adjudicaciones"),
    ],
)
def test_table_name_qualified(entity, expected) -> None:
    assert table_name(entity) == expected


def test_table_name_unqualified() -> None:
    assert table_name("empresa", qualified=False) == "proveedores"


def test_project_columns_only_keeps_mapped_fields() -> None:
    mapping = table_for("licitacion")
    payload = {
        "external_id": "1000-1-LR26",
        "title": "Compra",
        "status": "ADJUDICADA",
        "unknown_field": "ignored",
        "agency_code": None,
    }

    projected = project_columns(mapping, payload)

    assert projected == {
        "external_id": "1000-1-LR26",
        "title": "Compra",
        "status": "ADJUDICADA",
    }
    assert "unknown_field" not in projected
    assert "agency_code" not in projected


def test_project_columns_keeps_adjudicacion_metrics() -> None:
    mapping = table_for("adjudicacion")
    payload = {
        "external_id": "1000-44-LR26",
        "awarded_amount": 1500000,
        "estimated_amount": 2000000,
        "award_ratio": 0.75,
        "offers_count": 6,
        "quality_flags": [],
    }

    projected = project_columns(mapping, payload)

    assert projected["awarded_amount"] == 1500000
    assert projected["award_ratio"] == 0.75
    assert projected["quality_flags"] == []
