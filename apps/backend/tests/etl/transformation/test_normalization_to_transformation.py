from __future__ import annotations

from datetime import datetime, timezone

from app.etl.transformation.router import default_transformation_router
from app.integrations.chilecompra.parsers.adjudicaciones import (
    normalize_adjudicaciones,
)
from app.integrations.chilecompra.parsers.contratos import normalize_contratos
from app.integrations.chilecompra.parsers.convenios_marco import (
    normalize_convenios_marco,
)
from app.integrations.chilecompra.parsers.empresas import normalize_empresas
from app.integrations.chilecompra.parsers.licitaciones import normalize_licitaciones
from app.integrations.chilecompra.parsers.ordenes_compra import (
    normalize_ordenes_compra,
)

_AWARE = timezone.utc


def _normalize_and_transform(normalize, transformed_payload):
    normalized_items = normalize({"Listado": [transformed_payload]})
    assert len(normalized_items) == 1
    router = default_transformation_router()
    return router.transform(normalized_items[0].model_dump())


def test_licitacion_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_licitaciones,
        {
            "CodigoExterno": "1000-1-LR26",
            "Nombre": "Compra de equipamiento",
            "Estado": "Publicada",
            "FechaPublicacion": "2026-08-06",
            "FechaCierre": "2026-08-20",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
        },
    )

    assert result.entity == "licitacion"
    assert result.natural_key == "chilecompra:licitacion:1000-1-LR26"
    assert result.payload["nombre"] == "Compra de equipamiento"
    assert result.payload["estado"] == "PUBLICADA"
    assert result.payload["agency_code"] == "701"
    assert result.payload["fecha_publicacion"] is not None
    assert result.payload["fecha_cierre"] is not None


def test_orden_compra_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_ordenes_compra,
        {
            "CodigoOrdenCompra": "2580-120-SE26",
            "Nombre": "Compra de insumos",
            "Estado": "Emitida",
            "FechaCreacion": "2026-08-06",
            "FechaEmision": "2026-08-07",
            "CodigoProveedor": "76123456-7",
            "NombreProveedor": "Proveedor Demo SPA",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "MontoTotal": 2340000,
        },
    )

    assert result.entity == "orden_compra"
    assert result.payload["external_id"] == "2580-120-SE26"
    assert result.payload["provider_code"] == "76123456-7"
    assert result.payload["total_amount"] == 2340000


def test_empresa_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_empresas,
        {
            "CodigoEmpresa": "EMP-001",
            "Rut": "76123456-7",
            "NombreEmpresa": "Proveedor Demo SPA",
            "RazonSocial": "Proveedor Demo SpA",
            "TipoEmpresa": "PROVEEDOR",
            "Estado": "Activo",
            "FechaActualizacion": "2026-08-06",
        },
    )

    assert result.entity == "empresa"
    assert result.payload["rut"] == "76123456-7"
    assert result.payload["name"] == "Proveedor Demo SPA"
    assert result.payload["status"] == "ACTIVO"


def test_contrato_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_contratos,
        {
            "CodigoContrato": "2580-300-LR26",
            "Nombre": "Contrato de soporte clinico",
            "Estado": "Vigente",
            "FechaCreacion": "2026-08-06",
            "FechaInicio": "2026-08-07",
            "FechaFin": "2027-08-07",
            "CodigoProveedor": "76123456-7",
            "NombreProveedor": "Proveedor Demo SPA",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "MontoTotal": 8500000,
        },
    )

    assert result.entity == "contrato"
    assert result.payload["start_at"] is not None
    assert result.payload["end_at"] is not None
    assert result.payload["total_amount"] == 8500000


def test_convenio_marco_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_convenios_marco,
        {
            "CodigoConvenio": "2239-17-LR26",
            "Nombre": "Convenio de equipamiento asistencial",
            "Estado": "Vigente",
            "FechaCreacion": "2026-08-06",
            "FechaInicio": "2026-08-07",
            "FechaFin": "2027-08-07",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "MontoTotal": 19000000,
        },
    )

    assert result.entity == "convenio_marco"
    assert result.payload["external_id"] == "2239-17-LR26"
    assert result.payload["total_amount"] == 19000000


def test_adjudicacion_normalization_to_transformation() -> None:
    result = _normalize_and_transform(
        normalize_adjudicaciones,
        {
            "CodigoAdjudicacion": "1000-44-LR26",
            "Nombre": "Adjudicacion de equipos clinicos",
            "Estado": "Adjudicada",
            "FechaPublicacion": "2026-08-06",
            "FechaAdjudicacion": "2026-08-12",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "CodigoProveedor": "76123456-7",
            "NombreProveedor": "Proveedor Demo SPA",
            "MontoAdjudicado": "1500000",
            "MontoEstimado": "2000000",
            "CantidadOfertas": "6",
        },
    )

    assert result.entity == "adjudicacion"
    assert result.payload["awarded_amount"] == 1500000
    assert result.payload["estimated_amount"] == 2000000
    assert result.payload["award_ratio"] == 0.75
    assert result.payload["offers_count"] == 6
    assert result.payload["quality_flags"] == []


def test_normalized_payload_traces_raw_source_id() -> None:
    result = _normalize_and_transform(
        normalize_licitaciones,
        {
            "CodigoExterno": "1000-1-LR26",
            "Nombre": "Compra",
            "Estado": "Publicada",
        },
    )
    assert result.source_id == "1000-1-LR26"
    assert result.payload_hash
    assert isinstance(_AWARE, timezone)
