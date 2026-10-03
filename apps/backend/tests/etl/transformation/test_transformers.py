from __future__ import annotations

from datetime import datetime, timezone

from app.etl.transformation.adjudicaciones import AdjudicacionesTransformer
from app.etl.transformation.contratos import ContratosTransformer
from app.etl.transformation.convenios_marco import ConveniosMarcoTransformer
from app.etl.transformation.empresas import EmpresasTransformer
from app.etl.transformation.licitaciones import LicitacionesTransformer
from app.etl.transformation.ordenes_compra import OrdenesCompraTransformer

_AWARE = timezone.utc


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=_AWARE)


def test_licitaciones_transformer_maps_normalized_payload() -> None:
    transformer = LicitacionesTransformer()
    result = transformer.transform(
        {
            "external_id": "1000-1-LR26",
            "title": "Compra de equipamiento",
            "status": "ADJUDICADA",
            "published_at": _dt("2026-08-06T00:00:00+00:00"),
            "closing_at": _dt("2026-08-20T00:00:00+00:00"),
            "agency_code": "701",
            "agency_name": "Servicio Nacional",
            "raw_payload": {"Listado": []},
        }
    )

    assert result.entity == "licitacion"
    assert result.natural_key == "chilecompra:licitacion:1000-1-LR26"
    assert result.source_id == "1000-1-LR26"
    assert result.payload["codigo"] == "1000-1-LR26"
    assert result.payload["nombre"] == "Compra de equipamiento"
    assert result.payload["estado"] == "ADJUDICADA"
    assert result.payload["fecha_publicacion"] == "2026-08-06T00:00:00+00:00"
    assert result.payload["fecha_cierre"] == "2026-08-20T00:00:00+00:00"
    assert result.payload["agency_code"] == "701"
    assert "raw_payload" not in result.payload
    assert len(result.payload_hash) == 64


def test_licitaciones_transformer_drops_none_values() -> None:
    transformer = LicitacionesTransformer()
    result = transformer.transform(
        {
            "external_id": "1000-1-LR26",
            "title": "Compra de equipamiento",
            "status": "ADJUDICADA",
            "published_at": None,
            "closing_at": None,
            "agency_code": None,
            "agency_name": None,
            "raw_payload": {},
        }
    )

    assert "fecha_publicacion" not in result.payload
    assert "fecha_cierre" not in result.payload
    assert "agency_code" not in result.payload


def test_ordenes_compra_transformer_maps_normalized_payload() -> None:
    transformer = OrdenesCompraTransformer()
    result = transformer.transform(
        {
            "external_id": "2580-120-SE26",
            "title": "Compra de insumos",
            "status": "EMITIDA",
            "created_at": _dt("2026-08-06T00:00:00+00:00"),
            "issued_at": _dt("2026-08-07T00:00:00+00:00"),
            "provider_code": "76123456-7",
            "provider_name": "Proveedor Demo SPA",
            "agency_code": "701",
            "agency_name": "Servicio Nacional",
            "total_amount": 2340000,
            "raw_payload": {},
        }
    )

    assert result.entity == "orden_compra"
    assert result.payload["external_id"] == "2580-120-SE26"
    assert result.payload["provider_code"] == "76123456-7"
    assert result.payload["total_amount"] == 2340000
    assert result.payload["issued_at"] == "2026-08-07T00:00:00+00:00"


def test_empresas_transformer_maps_normalized_payload() -> None:
    transformer = EmpresasTransformer()
    result = transformer.transform(
        {
            "external_id": "EMP-001",
            "rut": "76123456-7",
            "name": "Proveedor Demo SPA",
            "legal_name": "Proveedor Demo SpA",
            "company_type": "PROVEEDOR",
            "status": "ACTIVO",
            "updated_at": _dt("2026-08-06T00:00:00+00:00"),
            "raw_payload": {},
        }
    )

    assert result.entity == "empresa"
    assert result.natural_key == "chilecompra:empresa:EMP-001"
    assert result.payload["rut"] == "76123456-7"
    assert result.payload["name"] == "Proveedor Demo SPA"
    assert result.payload["company_type"] == "PROVEEDOR"
    assert result.payload["updated_at"] == "2026-08-06T00:00:00+00:00"


def test_contratos_transformer_maps_normalized_payload() -> None:
    transformer = ContratosTransformer()
    result = transformer.transform(
        {
            "external_id": "2580-300-LR26",
            "title": "Contrato de soporte clinico",
            "status": "VIGENTE",
            "created_at": _dt("2026-08-06T00:00:00+00:00"),
            "start_at": _dt("2026-08-07T00:00:00+00:00"),
            "end_at": _dt("2027-08-07T00:00:00+00:00"),
            "provider_code": "76123456-7",
            "provider_name": "Proveedor Demo SPA",
            "agency_code": "701",
            "agency_name": "Servicio Nacional",
            "total_amount": 8500000,
            "raw_payload": {},
        }
    )

    assert result.entity == "contrato"
    assert result.natural_key == "chilecompra:contrato:2580-300-LR26"
    assert result.payload["start_at"] == "2026-08-07T00:00:00+00:00"
    assert result.payload["end_at"] == "2027-08-07T00:00:00+00:00"
    assert result.payload["total_amount"] == 8500000


def test_convenios_marco_transformer_maps_normalized_payload() -> None:
    transformer = ConveniosMarcoTransformer()
    result = transformer.transform(
        {
            "external_id": "2239-17-LR26",
            "title": "Convenio de equipamiento asistencial",
            "status": "VIGENTE",
            "created_at": _dt("2026-08-06T00:00:00+00:00"),
            "start_at": _dt("2026-08-07T00:00:00+00:00"),
            "end_at": _dt("2027-08-07T00:00:00+00:00"),
            "agency_code": "701",
            "agency_name": "Servicio Nacional",
            "total_amount": 19000000,
        }
    )

    assert result.entity == "convenio_marco"
    assert result.natural_key == "chilecompra:convenio_marco:2239-17-LR26"
    assert result.payload["total_amount"] == 19000000
    assert result.payload["agency_name"] == "Servicio Nacional"


def test_adjudicaciones_transformer_maps_normalized_payload() -> None:
    transformer = AdjudicacionesTransformer()
    result = transformer.transform(
        {
            "external_id": "1000-44-LR26",
            "title": "Adjudicacion de equipos clinicos",
            "status": "ADJUDICADA",
            "published_at": _dt("2026-08-06T00:00:00+00:00"),
            "awarded_at": _dt("2026-08-12T00:00:00+00:00"),
            "agency_code": "701",
            "provider_code": "76123456-7",
            "awarded_amount": 1500000,
            "estimated_amount": 2000000,
            "award_ratio": 0.75,
            "offers_count": 6,
            "quality_flags": [],
        }
    )

    assert result.entity == "adjudicacion"
    assert result.natural_key == "chilecompra:adjudicacion:1000-44-LR26"
    assert result.payload["awarded_amount"] == 1500000
    assert result.payload["estimated_amount"] == 2000000
    assert result.payload["award_ratio"] == 0.75
    assert result.payload["offers_count"] == 6
    assert result.payload["quality_flags"] == []


def test_transformers_produce_stable_hash_for_equal_payloads() -> None:
    transformer = LicitacionesTransformer()
    base = {
        "external_id": "1000-1-LR26",
        "title": "Compra",
        "status": "PUBLICADA",
    }
    first = transformer.transform(dict(base))
    second = transformer.transform(dict(base))

    assert first.payload_hash == second.payload_hash
    assert first.natural_key == second.natural_key
