from datetime import datetime, timezone

from app.etl.models import StoredRawRecord
from app.etl.validation.validators import (
    EmpresasRawValidator,
    OrdenesCompraRawValidator,
    ResourceValidationRouter,
    default_validation_router,
)


def test_ordenes_compra_validator_normalizes_valid_payload() -> None:
    validator = OrdenesCompraRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="ordenes_compra",
            source_id="OC-100",
            payload={
                "CodigoOrdenCompra": "OC-100",
                "Nombre": "Orden de compra de prueba",
                "Estado": "aceptada",
                "FechaCreacion": "2026-08-01",
                "FechaEmision": "2026-08-02",
                "CodigoProveedor": "9001",
                "NombreProveedor": "Proveedor Demo",
                "CodigoOrganismo": "7001",
                "NombreOrganismo": "Hospital Base",
                "MontoTotal": 125000.0,
            },
            payload_hash="a" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-ordenes-1",
        )
    )

    assert result.is_valid is True
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "OC-100"
    assert result.normalized_payload["status"] == "ACEPTADA"
    assert result.normalized_payload["provider_code"] == "9001"


def test_ordenes_compra_validator_rejects_invalid_date() -> None:
    validator = OrdenesCompraRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="ordenes_compra",
            source_id="OC-101",
            payload={
                "CodigoOrdenCompra": "OC-101",
                "Estado": "ACEPTADA",
                "FechaCreacion": "2026-14-99",
            },
            payload_hash="b" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-ordenes-2",
        )
    )

    assert result.is_valid is False
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaCreacion"


def test_empresas_validator_normalizes_valid_payload() -> None:
    validator = EmpresasRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="empresas",
            source_id="EMP-100",
            payload={
                "CodigoEmpresa": "EMP-100",
                "Rut": "76.123.456-7",
                "NombreEmpresa": "Empresa Demo",
                "RazonSocial": "Empresa Demo SpA",
                "TipoEmpresa": "SPA",
                "Estado": "vigente",
                "FechaActualizacion": "2026-08-05",
            },
            payload_hash="c" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-empresas-1",
        )
    )

    assert result.is_valid is True
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "EMP-100"
    assert result.normalized_payload["status"] == "VIGENTE"
    assert result.normalized_payload["name"] == "Empresa Demo"


def test_empresas_validator_rejects_invalid_date() -> None:
    validator = EmpresasRawValidator()
    result = validator.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="empresas",
            source_id="EMP-101",
            payload={
                "CodigoEmpresa": "EMP-101",
                "NombreEmpresa": "Empresa Demo",
                "FechaActualizacion": "not-a-date",
            },
            payload_hash="d" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-empresas-2",
        )
    )

    assert result.is_valid is False
    assert result.issues[0].code == "invalid_date"
    assert result.issues[0].field == "FechaActualizacion"


def test_validation_router_dispatches_by_resource() -> None:
    router = default_validation_router()
    result = router.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="ordenes_compra",
            source_id="OC-102",
            payload={"CodigoOrdenCompra": "OC-102", "Estado": "aceptada"},
            payload_hash="e" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-router-1",
        )
    )

    assert result.is_valid is True
    assert result.normalized_payload is not None
    assert result.normalized_payload["external_id"] == "OC-102"


def test_validation_router_rejects_unknown_resource() -> None:
    router = ResourceValidationRouter(validators_by_resource={})
    result = router.validate(
        StoredRawRecord(
            source="chilecompra_api",
            resource="desconocido",
            source_id="X-1",
            payload={"id": "X-1"},
            payload_hash="f" * 64,
            received_at=datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc),
            ingestion_run_id="run-router-2",
        )
    )

    assert result.is_valid is False
    assert result.issues[0].code == "validator_not_found"
