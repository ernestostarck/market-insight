"""Unit tests for Intent Detection (Fase 9.4).

Tests accurate intent classification across all 10 canonical intents and entity extraction.
"""

from __future__ import annotations

import pytest

from app.ai.contracts import IntentType
from app.ai.intent import RuleBasedIntentDetector
from app.ai.interfaces import IntentDetector


@pytest.fixture
def detector() -> RuleBasedIntentDetector:
    return RuleBasedIntentDetector()


def test_intent_detector_satisfies_protocol(detector: RuleBasedIntentDetector) -> None:
    assert isinstance(detector, IntentDetector)


@pytest.mark.asyncio
async def test_detect_spending_analysis(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "¿Cuánto gastaron los municipios en sillas de ruedas durante 2025?",
        "Gasto total en medicamentos del hospital regional",
        "¿Cuál fue el monto total adjudicado en 2024?",
        "Presupuesto ejecutado por el Ministerio de Salud",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.SPENDING_ANALYSIS, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_price_analysis(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "¿Cuál es el precio promedio de las ambulancias?",
        "Costo unitario de mascarillas quirúrgicas",
        "¿A qué precio se compraron los computadores portátiles?",
        "Valor promedio unitario de insumos de laboratorio",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.PRICE_ANALYSIS, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_supplier_analysis(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "¿Qué proveedores ganaron más adjudicaciones este año?",
        "Desempeño del proveedor con RUT 76.123.456-7",
        "¿Quién ganó el contrato de suministro de servidores?",
        "Ranking de proveedores en la categoría de tecnología",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.SUPPLIER_ANALYSIS, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_organization_analysis(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "¿Qué compras ha realizado la Municipalidad de Las Condes?",
        "Actividad del organismo comprador Hospital San Juan",
        "Compras de la entidad compradora Servicio de Salud Metropolitano",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.ORGANIZATION_ANALYSIS, f"Failed for query: {q}"
        assert confidence >= 0.80


@pytest.mark.asyncio
async def test_detect_trend_analysis(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "¿Cuál es la evolución mensual del gasto en tecnología durante 2024?",
        "Tendencia de compras mes a mes en el mercado de alimentos",
        "Comportamiento temporal del gasto público en salud",
        "Histórico mensual de licitaciones publicadas",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.TREND_ANALYSIS, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_comparison(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "Comparar el gasto entre el Ministerio de Salud y el Ministerio de Educación",
        "Diferencia entre el año 2024 y 2025 en adquisición de vehículos",
        "¿Cuál gastó más entre la Municipalidad de Santiago y la de Valparaíso?",
        "Gasto de Minsal versus Mineduc",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.COMPARISON, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_detail_lookup(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "Buscar detalles de la licitación 721-12-LP24",
        "Información sobre la orden de compra 234-56-OC24",
        "Consultar licitación 1058-2-LE23",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.DETAIL_LOOKUP, f"Failed for query: {q}"
        assert confidence >= 0.95


@pytest.mark.asyncio
async def test_detect_semantic_search(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "Encuentra productos relacionados con movilidad asistida",
        "Equipamiento similar a ecógrafos portátiles",
        "Conceptos afines a instrumental quirúrgico",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.SEMANTIC_SEARCH, f"Failed for query: {q}"
        assert confidence >= 0.85


@pytest.mark.asyncio
async def test_detect_search(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "Buscar licitaciones de insumos de oficina",
        "Encuentra licitaciones de computadores",
        "Mostrar compras públicas de útiles escolares",
    ]
    for q in queries:
        intent, confidence = await detector.detect_intent(q)
        assert intent == IntentType.SEARCH, f"Failed for query: {q}"
        assert confidence >= 0.70


@pytest.mark.asyncio
async def test_detect_unknown_or_out_of_scope(detector: RuleBasedIntentDetector) -> None:
    queries = [
        "Hola",
        "Buenos días",
        "¿Cómo estás hoy?",
        "Receta de cazuela de vacuno",
        "¿Quién ganó el mundial de fútbol?",
    ]
    for q in queries:
        intent, _ = await detector.detect_intent(q)
        assert intent == IntentType.UNKNOWN, f"Failed for query: {q}"


def test_extract_entities_from_query(detector: RuleBasedIntentDetector) -> None:
    text = "Licitación 721-12-LP24 de la empresa con RUT 76.123.456-7 durante 2025 y orden 99-1-OC25"
    entities = detector.extract_entities(text)

    assert entities["tender_id"] == "721-12-LP24"
    assert entities["order_id"] == "99-1-OC25"
    assert entities["rut"] == "76.123.456-7"
    assert 2025 in entities["years"]
