from __future__ import annotations

from app.integrations.chilecompra.parsers.adjudicaciones import (
    analyze_adjudicaciones,
    normalize_adjudicaciones,
    parse_adjudicaciones_payload,
)
from app.integrations.chilecompra.parsers.contratos import (
    normalize_contratos,
    parse_contratos_payload,
)
from app.integrations.chilecompra.parsers.convenios_marco import (
    normalize_convenios_marco,
    parse_convenios_marco_payload,
)
from app.integrations.chilecompra.parsers.empresas import (
    normalize_empresas,
    parse_empresas_payload,
)
from app.integrations.chilecompra.parsers.licitaciones import (
    normalize_licitaciones,
    parse_licitacion_detalle,
    parse_licitaciones_payload,
)
from app.integrations.chilecompra.parsers.ordenes_compra import (
    normalize_ordenes_compra,
    parse_ordenes_compra_payload,
)


def test_parse_licitaciones_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "1000-1-LP26",
                "Nombre": "Licitacion de prueba",
                "Estado": "Publicada",
            }
        ],
    }

    parsed = parse_licitaciones_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_externo == "1000-1-LP26"


def test_parse_licitaciones_payload_from_list() -> None:
    payload = [{"CodigoExterno": "1000-1-LP26", "Nombre": "Licitacion"}]

    parsed = parse_licitaciones_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].codigo_externo == "1000-1-LP26"


def test_normalize_licitaciones_for_etl_input() -> None:
    payload = {
        "Listado": [
            {
                "CodigoExterno": "1000-1-LP26",
                "Nombre": "Compra de equipamiento",
                "Estado": "Publicada",
                "FechaPublicacion": "20260806",
                "FechaCierre": "10082026",
                "CodigoOrganismo": "701",
                "NombreOrganismo": "Servicio Nacional",
            }
        ]
    }

    normalized = normalize_licitaciones(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "1000-1-LP26"
    assert normalized[0].title == "Compra de equipamiento"
    assert normalized[0].status == "PUBLICADA"
    assert normalized[0].agency_code == "701"
    assert normalized[0].agency_name == "Servicio Nacional"
    assert normalized[0].published_at is not None
    assert normalized[0].closing_at is not None


def test_parse_licitacion_detalle_extracts_items_descripcion_and_organismo() -> None:
    payload = {
        "Listado": [
            {
                "CodigoExterno": "1002588-89-LE26",
                "Descripcion": "Adquirir materiales e insumos para talleres extraescolares.",
                "Comprador": {
                    "CodigoOrganismo": "1593366",
                    "NombreOrganismo": "SERVICIO LOCAL DE EDUCACION",
                    "ComunaUnidad": "Coquimbo",
                    "RegionUnidad": "Region de Coquimbo",
                },
                "Fechas": {
                    "FechaPublicacion": "2026-08-10T13:45:28.563",
                    "FechaCierre": "2026-08-20T14:23:00",
                },
                "Items": {
                    "Cantidad": 1,
                    "Listado": [
                        {
                            "Correlativo": 1,
                            "CodigoProducto": 11162110,
                            "CodigoCategoria": "11162100",
                            "Categoria": "Tejidos especiales",
                            "NombreProducto": "Tul",
                            "Descripcion": "Linea N1: Telas e insumos para taller de teatro",
                            "UnidadMedida": "Unidad",
                            "Cantidad": 1.0,
                        }
                    ],
                },
            }
        ]
    }

    detail = parse_licitacion_detalle(payload)

    assert detail is not None
    assert detail.external_id == "1002588-89-LE26"
    assert detail.descripcion.startswith("Adquirir materiales")
    assert detail.agency_code == "1593366"
    assert detail.agency_name == "SERVICIO LOCAL DE EDUCACION"
    assert detail.agency_comuna == "Coquimbo"
    assert detail.published_at is not None
    assert detail.closing_at is not None
    assert len(detail.items) == 1
    assert detail.items[0].correlativo == 1
    assert detail.items[0].nombre_producto == "Tul"
    assert detail.items[0].cantidad == 1.0


def test_parse_licitacion_detalle_returns_none_for_empty_listado() -> None:
    assert parse_licitacion_detalle({"Listado": []}) is None
    assert parse_licitacion_detalle({}) is None


def test_parse_ordenes_compra_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoOrdenCompra": "2580-120-SE26",
                "Nombre": "Orden de compra de prueba",
                "Estado": "Emitida",
            }
        ],
    }

    parsed = parse_ordenes_compra_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_orden_compra == "2580-120-SE26"


def test_parse_ordenes_compra_payload_from_list() -> None:
    payload = [{"CodigoOrdenCompra": "2580-120-SE26", "Nombre": "Orden"}]

    parsed = parse_ordenes_compra_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].codigo_orden_compra == "2580-120-SE26"


def test_normalize_ordenes_compra_for_etl_input() -> None:
    payload = {
        "Listado": [
            {
                "CodigoOrdenCompra": "2580-120-SE26",
                "Nombre": "Compra de equipamiento medico",
                "Estado": "Emitida",
                "FechaCreacion": "20260806",
                "FechaEmision": "07082026",
                "CodigoProveedor": "76123456-7",
                "NombreProveedor": "Proveedor Demo SPA",
                "CodigoOrganismo": "701",
                "NombreOrganismo": "Servicio Nacional",
                "MontoTotal": 2340000,
            }
        ]
    }

    normalized = normalize_ordenes_compra(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "2580-120-SE26"
    assert normalized[0].title == "Compra de equipamiento medico"
    assert normalized[0].status == "EMITIDA"
    assert normalized[0].provider_code == "76123456-7"
    assert normalized[0].provider_name == "Proveedor Demo SPA"
    assert normalized[0].agency_code == "701"
    assert normalized[0].agency_name == "Servicio Nacional"
    assert normalized[0].total_amount == 2340000
    assert normalized[0].created_at is not None
    assert normalized[0].issued_at is not None


def test_parse_empresas_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoEmpresa": "EMP-001",
                "Rut": "76123456-7",
                "NombreEmpresa": "Proveedor Demo",
            }
        ],
    }

    parsed = parse_empresas_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_empresa == "EMP-001"


def test_parse_empresas_payload_from_list() -> None:
    payload = [
        {
            "CodigoEmpresa": "EMP-001",
            "Rut": "76123456-7",
            "NombreEmpresa": "Proveedor Demo",
        }
    ]

    parsed = parse_empresas_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].rut == "76123456-7"


def test_normalize_empresas_for_etl_input() -> None:
    payload = {
        "Listado": [
            {
                "CodigoEmpresa": "EMP-001",
                "Rut": "76123456-7",
                "NombreEmpresa": "Proveedor Demo SPA",
                "RazonSocial": "Proveedor Demo SpA",
                "TipoEmpresa": "PROVEEDOR",
                "Estado": "Activo",
                "FechaActualizacion": "2026-08-06",
            }
        ]
    }

    normalized = normalize_empresas(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "EMP-001"
    assert normalized[0].rut == "76123456-7"
    assert normalized[0].name == "Proveedor Demo SPA"
    assert normalized[0].legal_name == "Proveedor Demo SpA"
    assert normalized[0].company_type == "PROVEEDOR"
    assert normalized[0].status == "ACTIVO"
    assert normalized[0].updated_at is not None


def test_parse_contratos_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoContrato": "2580-300-LR26",
                "Nombre": "Contrato de soporte",
                "Estado": "Vigente",
            }
        ],
    }

    parsed = parse_contratos_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_contrato == "2580-300-LR26"


def test_parse_contratos_payload_from_list() -> None:
    payload = [{"CodigoContrato": "2580-300-LR26", "Nombre": "Contrato"}]

    parsed = parse_contratos_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].codigo_contrato == "2580-300-LR26"


def test_normalize_contratos_for_etl_input() -> None:
    payload = {
        "Listado": [
            {
                "CodigoContrato": "2580-300-LR26",
                "Nombre": "Contrato de soporte clinico",
                "Estado": "Vigente",
                "FechaCreacion": "20260806",
                "FechaInicio": "07082026",
                "FechaFin": "2027-08-07",
                "CodigoProveedor": "76123456-7",
                "NombreProveedor": "Proveedor Demo SPA",
                "CodigoOrganismo": "701",
                "NombreOrganismo": "Servicio Nacional",
                "MontoTotal": 8500000,
            }
        ]
    }

    normalized = normalize_contratos(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "2580-300-LR26"
    assert normalized[0].title == "Contrato de soporte clinico"
    assert normalized[0].status == "VIGENTE"
    assert normalized[0].provider_code == "76123456-7"
    assert normalized[0].provider_name == "Proveedor Demo SPA"
    assert normalized[0].agency_code == "701"
    assert normalized[0].agency_name == "Servicio Nacional"
    assert normalized[0].total_amount == 8500000
    assert normalized[0].created_at is not None
    assert normalized[0].start_at is not None
    assert normalized[0].end_at is not None


def test_parse_convenios_marco_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoConvenio": "2239-17-LR26",
                "Nombre": "Convenio de movilidad",
                "Estado": "Vigente",
            }
        ],
    }

    parsed = parse_convenios_marco_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_convenio == "2239-17-LR26"


def test_parse_convenios_marco_payload_from_list() -> None:
    payload = [{"CodigoConvenio": "2239-17-LR26", "Nombre": "Convenio"}]

    parsed = parse_convenios_marco_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].codigo_convenio == "2239-17-LR26"


def test_normalize_convenios_marco_for_etl_input() -> None:
    payload = {
        "Listado": [
            {
                "CodigoConvenio": "2239-17-LR26",
                "Nombre": "Convenio de equipamiento asistencial",
                "Estado": "Vigente",
                "FechaCreacion": "20260806",
                "FechaInicio": "07082026",
                "FechaFin": "2027-08-07",
                "CodigoOrganismo": "701",
                "NombreOrganismo": "Servicio Nacional",
                "MontoTotal": 19000000,
            }
        ]
    }

    normalized = normalize_convenios_marco(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "2239-17-LR26"
    assert normalized[0].title == "Convenio de equipamiento asistencial"
    assert normalized[0].status == "VIGENTE"
    assert normalized[0].agency_code == "701"
    assert normalized[0].agency_name == "Servicio Nacional"
    assert normalized[0].total_amount == 19000000
    assert normalized[0].created_at is not None
    assert normalized[0].start_at is not None
    assert normalized[0].end_at is not None


def test_parse_adjudicaciones_payload_from_dict() -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoAdjudicacion": "1000-44-LR26",
                "Nombre": "Adjudicacion de prueba",
                "Estado": "Adjudicada",
            }
        ],
    }

    parsed = parse_adjudicaciones_payload(payload)

    assert parsed.cantidad == 1
    assert len(parsed.listado) == 1
    assert parsed.listado[0].codigo_adjudicacion == "1000-44-LR26"


def test_parse_adjudicaciones_payload_from_list() -> None:
    payload = [{"CodigoAdjudicacion": "1000-44-LR26", "Nombre": "Adjudicacion"}]

    parsed = parse_adjudicaciones_payload(payload)

    assert parsed.cantidad == 1
    assert parsed.listado[0].codigo_adjudicacion == "1000-44-LR26"


def test_normalize_adjudicaciones_for_etl_input_with_metrics() -> None:
    payload = {
        "Listado": [
            {
                "CodigoAdjudicacion": "1000-44-LR26",
                "Nombre": "Adjudicacion de equipos clinicos",
                "Estado": "Adjudicada",
                "FechaPublicacion": "20260806",
                "FechaAdjudicacion": "12082026",
                "CodigoOrganismo": "701",
                "NombreOrganismo": "Servicio Nacional",
                "CodigoProveedor": "76123456-7",
                "NombreProveedor": "Proveedor Demo SPA",
                "MontoAdjudicado": "1500000",
                "MontoEstimado": "2000000",
                "CantidadOfertas": "6",
            }
        ]
    }

    normalized = normalize_adjudicaciones(payload)

    assert len(normalized) == 1
    assert normalized[0].external_id == "1000-44-LR26"
    assert normalized[0].title == "Adjudicacion de equipos clinicos"
    assert normalized[0].status == "ADJUDICADA"
    assert normalized[0].agency_code == "701"
    assert normalized[0].provider_code == "76123456-7"
    assert normalized[0].awarded_amount == 1500000
    assert normalized[0].estimated_amount == 2000000
    assert normalized[0].award_ratio == 0.75
    assert normalized[0].offers_count == 6
    assert normalized[0].quality_flags == []


def test_normalize_adjudicaciones_adds_quality_flags_when_missing_values() -> None:
    payload = {
        "Listado": [
            {
                "CodigoAdjudicacion": "1000-44-LR26",
                "Estado": "Adjudicada",
            }
        ]
    }

    normalized = normalize_adjudicaciones(payload)

    assert len(normalized) == 1
    assert "missing_title" in normalized[0].quality_flags
    assert "missing_awarded_amount" in normalized[0].quality_flags
    assert "missing_estimated_amount" in normalized[0].quality_flags
    assert "missing_offers_count" in normalized[0].quality_flags


def test_normalize_adjudicaciones_marks_fallback_payload_from_licitaciones() -> None:
    payload = {
        "Listado": [
            {
                "CodigoExterno": "1000-44-LR26",
                "Nombre": "Adjudicacion derivada",
                "CodigoEstado": 8,
                "FechaCierre": "2026-08-06T15:00:00",
                "__source_resource": "licitaciones.json",
            }
        ],
        "__source_resource": "licitaciones.json",
    }

    normalized = normalize_adjudicaciones(payload)

    assert len(normalized) == 1
    assert "fallback_payload_from_licitaciones" in normalized[0].quality_flags
    assert "fallback_partial_adjudicacion_fields" in normalized[0].quality_flags
    assert "missing_awarded_amount" in normalized[0].quality_flags


def test_analyze_adjudicaciones_generates_summary_and_scores() -> None:
    payload = {
        "Listado": [
            {
                "CodigoAdjudicacion": "1000-44-LR26",
                "Nombre": "Adjudicacion A",
                "Estado": "Adjudicada",
                "MontoAdjudicado": "1000000",
                "MontoEstimado": "1500000",
                "CantidadOfertas": "6",
            },
            {
                "CodigoAdjudicacion": "1000-45-LR26",
                "Nombre": "Adjudicacion B",
                "Estado": "Adjudicada",
                "MontoAdjudicado": "9000000",
                "MontoEstimado": "3000000",
                "CantidadOfertas": "2",
            },
        ]
    }

    result = analyze_adjudicaciones(payload)

    assert result.summary.total_items == 2
    assert result.summary.scored_items == 2
    assert result.summary.avg_opportunity_score is not None
    assert len(result.items) == 2
    assert result.items[0].external_id == "1000-44-LR26"
    assert result.items[0].opportunity_score >= 0
    assert result.items[0].opportunity_score <= 100


def test_analyze_adjudicaciones_detects_outlier_by_ratio() -> None:
    payload = {
        "Listado": [
            {
                "CodigoAdjudicacion": "1000-99-LR26",
                "Nombre": "Adjudicacion outlier",
                "Estado": "Adjudicada",
                "MontoAdjudicado": "9000000",
                "MontoEstimado": "2000000",
                "CantidadOfertas": "3",
            }
        ]
    }

    result = analyze_adjudicaciones(payload)

    assert result.summary.outlier_items == 1
    assert result.items[0].is_outlier is True
    assert "high_award_ratio" in result.items[0].reasons


def test_analyze_adjudicaciones_adds_reason_for_fallback_source_data() -> None:
    payload = {
        "Listado": [
            {
                "CodigoExterno": "1000-99-LR26",
                "Nombre": "Adjudicacion fallback",
                "CodigoEstado": 8,
                "__source_resource": "licitaciones.json",
            }
        ]
    }

    result = analyze_adjudicaciones(payload)

    assert "fallback_source_data" in result.items[0].reasons
