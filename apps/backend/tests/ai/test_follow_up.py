"""Unit tests for FollowUpResolver (Fase 9.19)."""

from app.ai.follow_up import FollowUpResolver
from app.ai.memory import ConversationContextState


def test_resolve_ordinal_reference():
    resolver = FollowUpResolver()

    # Prior state has two suppliers discussed
    state = ConversationContextState(
        turn_count=1,
        active_market_category="sillas de ruedas",
        referenced_entities=[
            {"ordinal": 1, "type": "supplier", "name": "Ortopedia Vital SpA"},
            {"ordinal": 2, "type": "supplier", "name": "Movilidad Total Ltda"},
        ],
        active_filters={"categoria": "sillas de ruedas"},
    )

    # User follow-up asking about "el primero"
    res = resolver.resolve("¿Y cuánto vendió el primero?", state)

    assert res.is_follow_up is True
    assert "Ortopedia Vital SpA" in res.resolved_query
    assert res.merged_filters["proveedor_razon_social"] == "Ortopedia Vital SpA"
    assert res.merged_filters["categoria"] == "sillas de ruedas"


def test_resolve_delta_year_modification():
    resolver = FollowUpResolver()

    # Previous question was: "¿Cuánto gastaron los municipios en sillas de ruedas en 2025?"
    state = ConversationContextState(
        turn_count=1,
        active_organization="Municipalidades",
        active_market_category="sillas de ruedas",
        active_filters={"region": "Metropolitana", "year": 2025},
        active_time_range={"year": 2025},
    )

    # Follow-up: "¿Y en 2024?"
    res = resolver.resolve("¿Y en 2024?", state)

    assert res.is_follow_up is True
    assert res.merged_filters["year"] == 2024
    assert res.merged_filters["region"] == "Metropolitana"
    assert "2024" in res.resolved_query


def test_resolve_demonstrative_reference():
    resolver = FollowUpResolver()

    state = ConversationContextState(
        turn_count=1,
        active_supplier="Insumos Médicos Sur SpA",
        active_organization="Hospital San Borja",
        active_filters={},
    )

    # Follow-up asking about "ese proveedor"
    res_supp = resolver.resolve("¿Qué licitaciones ganó ese proveedor?", state)
    assert res_supp.is_follow_up is True
    assert "Insumos Médicos Sur SpA" in res_supp.resolved_query
    assert res_supp.merged_filters["proveedor_razon_social"] == "Insumos Médicos Sur SpA"

    # Follow-up asking about "ese hospital"
    res_hosp = resolver.resolve("¿Cuál fue el presupuesto de ese hospital?", state)
    assert res_hosp.is_follow_up is True
    assert "Hospital San Borja" in res_hosp.resolved_query
    assert res_hosp.merged_filters["comprador_nombre"] == "Hospital San Borja"


def test_ambiguity_triggers_clarification_prompt():
    resolver = FollowUpResolver()

    # Three suppliers in state
    state = ConversationContextState(
        turn_count=2,
        referenced_entities=[
            {"ordinal": 1, "name": "Proveedor A"},
            {"ordinal": 2, "name": "Proveedor B"},
            {"ordinal": 3, "name": "Proveedor C"},
        ],
    )

    # Ambiguous query without specifying which one
    res = resolver.resolve("¿Cuánto vendió?", state)
    assert res.needs_clarification is True
    assert res.clarification_message is not None
    assert "Proveedor A" in res.clarification_message
    assert "Proveedor B" in res.clarification_message
