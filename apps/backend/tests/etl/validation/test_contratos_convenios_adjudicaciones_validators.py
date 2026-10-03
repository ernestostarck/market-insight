"""Tests for the Fase 3.5 resource validators (contratos, convenios_marco,
adjudicaciones).

These mirror the established validation contract: a valid payload is schema
validated, normalized, and its dates checked; an invalid payload is rejected
with a precise issue code.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.etl.models import StoredRawRecord
from app.etl.validation.validators import (
    AdjudicacionesRawValidator,
    ContratosRawValidator,
    ConveniosMarcoRawValidator,
)


def _record(
    resource: str,
    source_id: str,
    payload: dict,
    *,
    run: str = "run-1",
) -> StoredRawRecord:
    return StoredRawRecord(
        source="chilecompra_api",
        resource=resource,
        source_id=source_id,
        payload=payload,
        payload_hash="f" * 64,
        received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
        ingestion_run_id=run,
    )


# --------------------------------------------------------------------- #
# Contratos
# --------------------------------------------------------------------- #
def test_contratos_validator_normalizes_valid_payload() -> None:
    record = _record(
        "contratos",
        "2580-300-LR26",
        {
            "CodigoContrato": "2580-300-LR26",
            "Nombre": "Contrato de soporte clinico",
            "Estado": "Vigente",
            "FechaCreacion": "2026-08-01",
            "FechaInicio": "2026-08-02",
            "FechaFin": "2027-08-02",
            "CodigoProveedor": "76123456-7",
            "NombreProveedor": "Proveedor Demo SPA",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "MontoTotal": 8500000,
        },
    )

    result = ContratosRawValidator().validate(record)

    assert result.is_valid is True
    assert result.issues == []
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "2580-300-LR26"
    assert result.normalized_payload["status"] == "VIGENTE"
    assert result.normalized_payload["provider_code"] == "76123456-7"
    assert result.normalized_payload["agency_code"] == "701"
    assert result.normalized_payload["total_amount"] == 8500000


def test_contratos_validator_rejects_invalid_date() -> None:
    record = _record(
        "contratos",
        "2580-300-LR26",
        {
            "CodigoContrato": "2580-300-LR26",
            "Estado": "VIGENTE",
            "FechaFin": "not-a-date",
        },
    )

    result = ContratosRawValidator().validate(record)

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaFin"


def test_contratos_validator_rejects_missing_codigo() -> None:
    record = _record(
        "contratos",
        "missing-code",
        {"Nombre": "Contrato sin codigo", "Estado": "VIGENTE"},
    )

    result = ContratosRawValidator().validate(record)

    assert result.is_valid is False
    assert result.normalized_payload is None
    # Without any codigo the schema passes (all codigo fields are optional),
    # so the normalization step rejects it with a normalization_error.
    assert result.issues[0].code == "normalization_error"


# --------------------------------------------------------------------- #
# Convenios Marco
# --------------------------------------------------------------------- #
def test_convenios_marco_validator_normalizes_valid_payload() -> None:
    record = _record(
        "convenios_marco",
        "2239-17-LR26",
        {
            "CodigoConvenio": "2239-17-LR26",
            "Nombre": "Convenio de equipamiento asistencial",
            "Estado": "Vigente",
            "FechaCreacion": "2026-08-01",
            "FechaInicio": "2026-08-02",
            "FechaFin": "2027-08-02",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "MontoTotal": 19000000,
        },
    )

    result = ConveniosMarcoRawValidator().validate(record)

    assert result.is_valid is True
    assert result.issues == []
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "2239-17-LR26"
    assert result.normalized_payload["status"] == "VIGENTE"
    assert result.normalized_payload["agency_code"] == "701"
    assert result.normalized_payload["total_amount"] == 19000000


def test_convenios_marco_validator_rejects_invalid_date() -> None:
    record = _record(
        "convenios_marco",
        "2239-17-LR26",
        {
            "CodigoConvenio": "2239-17-LR26",
            "Estado": "VIGENTE",
            "FechaInicio": "32/13/2030",
        },
    )

    result = ConveniosMarcoRawValidator().validate(record)

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaInicio"


# --------------------------------------------------------------------- #
# Adjudicaciones
# --------------------------------------------------------------------- #
def test_adjudicaciones_validator_normalizes_valid_payload() -> None:
    record = _record(
        "adjudicaciones",
        "1000-44-LR26",
        {
            "CodigoAdjudicacion": "1000-44-LR26",
            "Nombre": "Adjudicacion de equipos clinicos",
            "Estado": "Adjudicada",
            "FechaPublicacion": "2026-08-01",
            "FechaAdjudicacion": "2026-08-02",
            "CodigoOrganismo": "701",
            "NombreOrganismo": "Servicio Nacional",
            "CodigoProveedor": "76123456-7",
            "NombreProveedor": "Proveedor Demo SPA",
            "MontoAdjudicado": "1500000",
            "MontoEstimado": "2000000",
            "CantidadOfertas": "6",
        },
    )

    result = AdjudicacionesRawValidator().validate(record)

    assert result.is_valid is True
    assert result.issues == []
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "1000-44-LR26"
    assert result.normalized_payload["status"] == "ADJUDICADA"
    assert result.normalized_payload["awarded_amount"] == 1500000
    assert result.normalized_payload["award_ratio"] == 0.75
    assert result.normalized_payload["offers_count"] == 6


def test_adjudicaciones_validator_rejects_invalid_date() -> None:
    record = _record(
        "adjudicaciones",
        "1000-44-LR26",
        {
            "CodigoAdjudicacion": "1000-44-LR26",
            "Estado": "ADJUDICADA",
            "FechaAdjudicacion": "2026/99/99",
        },
    )

    result = AdjudicacionesRawValidator().validate(record)

    assert result.is_valid is False
    assert result.normalized_payload is None
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaAdjudicacion"


def test_adjudicaciones_validator_accepts_fallback_payload() -> None:
    """Adjudicaciones derived from licitaciones fallback are still valid."""
    record = _record(
        "adjudicaciones",
        "1000-44-LR26",
        {
            "CodigoExterno": "1000-44-LR26",
            "Nombre": "Adjudicacion derivada",
            "CodigoEstado": 8,
            "FechaCierre": "2026-08-06T15:00:00",
            "__source_resource": "licitaciones.json",
        },
    )

    result = AdjudicacionesRawValidator().validate(record)

    assert result.is_valid is True
    assert result.normalized_payload is not None
    assert (
        "fallback_payload_from_licitaciones"
        in result.normalized_payload["quality_flags"]
    )


# --------------------------------------------------------------------- #
# Router integration
# --------------------------------------------------------------------- #
def test_router_dispatches_contratos_convenios_adjudicaciones() -> None:
    from app.etl.validation.validators import default_validation_router

    router = default_validation_router()

    for resource, payload in {
        "contratos": {
            "CodigoContrato": "2580-300-LR26",
            "Estado": "VIGENTE",
        },
        "convenios_marco": {
            "CodigoConvenio": "2239-17-LR26",
            "Estado": "VIGENTE",
        },
        "adjudicaciones": {
            "CodigoAdjudicacion": "1000-44-LR26",
            "Estado": "ADJUDICADA",
        },
    }.items():
        result = router.validate(_record(resource, "x", payload))
        assert result.is_valid is True, f"{resource} should be dispatched"
        assert result.normalized_payload is not None
