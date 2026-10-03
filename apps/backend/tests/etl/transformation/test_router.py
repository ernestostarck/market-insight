from __future__ import annotations

from datetime import datetime, timezone

from app.etl.transformation.router import (
    TransformationRouter,
    default_transformation_router,
)

_AWARE = timezone.utc


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=_AWARE)


def _router() -> TransformationRouter:
    return default_transformation_router()


def test_router_infers_licitacion() -> None:
    result = _router().transform(
        {
            "external_id": "1000-1-LR26",
            "title": "Compra",
            "status": "PUBLICADA",
            "closing_at": _dt("2026-08-20T00:00:00+00:00"),
        }
    )
    assert result.entity == "licitacion"


def test_router_infers_orden_compra() -> None:
    result = _router().transform(
        {
            "external_id": "2580-120-SE26",
            "title": "Orden",
            "status": "EMITIDA",
            "issued_at": _dt("2026-08-07T00:00:00+00:00"),
        }
    )
    assert result.entity == "orden_compra"


def test_router_infers_empresa() -> None:
    result = _router().transform(
        {
            "external_id": "EMP-001",
            "rut": "76123456-7",
            "name": "Proveedor Demo",
        }
    )
    assert result.entity == "empresa"


def test_router_infers_contrato() -> None:
    result = _router().transform(
        {
            "external_id": "2580-300-LR26",
            "title": "Contrato",
            "status": "VIGENTE",
            "provider_code": "76123456-7",
            "start_at": _dt("2026-08-07T00:00:00+00:00"),
            "end_at": _dt("2027-08-07T00:00:00+00:00"),
        }
    )
    assert result.entity == "contrato"


def test_router_infers_convenio_marco() -> None:
    result = _router().transform(
        {
            "external_id": "2239-17-LR26",
            "title": "Convenio",
            "status": "VIGENTE",
            "start_at": _dt("2026-08-07T00:00:00+00:00"),
            "end_at": _dt("2027-08-07T00:00:00+00:00"),
        }
    )
    assert result.entity == "convenio_marco"


def test_router_infers_adjudicacion() -> None:
    result = _router().transform(
        {
            "external_id": "1000-44-LR26",
            "title": "Adjudicacion",
            "status": "ADJUDICADA",
            "awarded_at": _dt("2026-08-12T00:00:00+00:00"),
            "award_ratio": 0.75,
        }
    )
    assert result.entity == "adjudicacion"


def test_router_falls_back_to_unknown_entity() -> None:
    result = _router().transform(
        {
            "external_id": "X-1",
            "title": "Desconocido",
        }
    )
    assert result.entity == "unknown"
    assert result.natural_key == "chilecompra:unknown:X-1"


def test_router_builds_stable_natural_keys_per_entity() -> None:
    router = _router()
    licitacion = router.transform(
        {"external_id": "1000-1-LR26", "closing_at": _dt("2026-08-20T00:00:00+00:00")}
    )
    adjudicacion = router.transform(
        {
            "external_id": "1000-1-LR26",
            "awarded_at": _dt("2026-08-12T00:00:00+00:00"),
            "award_ratio": 0.5,
        }
    )

    assert licitacion.natural_key != adjudicacion.natural_key
    assert licitacion.natural_key == "chilecompra:licitacion:1000-1-LR26"
    assert adjudicacion.natural_key == "chilecompra:adjudicacion:1000-1-LR26"
