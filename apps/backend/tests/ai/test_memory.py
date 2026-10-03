"""Unit tests for ConversationMemoryManager (Fase 9.18)."""

from app.ai.contracts import ChatMessage, MessageRole
from app.ai.memory import ConversationContextState, ConversationMemoryManager


def test_context_state_serialization_and_deserialization():
    manager = ConversationMemoryManager()

    state = ConversationContextState(
        active_filters={"region": "Metropolitana", "year": 2025},
        active_time_range={"year": 2025},
        active_market_category="sillas de ruedas",
        active_organization="Hospital San Juan",
        turn_count=3,
    )

    metadata: dict = {}
    persisted = manager.persist_context_state(metadata, state)
    assert "context_state" in persisted

    recovered = manager.get_context_state(persisted)
    assert recovered.active_filters["region"] == "Metropolitana"
    assert recovered.active_time_range["year"] == 2025
    assert recovered.active_market_category == "sillas de ruedas"
    assert recovered.active_organization == "Hospital San Juan"
    assert recovered.turn_count == 3


def test_update_context_state_with_entities_and_filters():
    manager = ConversationMemoryManager()
    initial_state = ConversationContextState()

    detected_entities = [
        {"type": "supplier", "value": "Tecnomed Chile SpA"},
        {"type": "organization", "value": "Municipalidad de Santiago"},
    ]
    query_filters = {"year": 2024, "categoria": "Equipos Médicos"}

    updated = manager.update_context_state(
        current_state=initial_state,
        query="¿Cuánto vendió Tecnomed a la Municipalidad en 2024?",
        detected_entities=detected_entities,
        query_filters=query_filters,
    )

    assert updated.turn_count == 1
    assert updated.active_supplier == "Tecnomed Chile SpA"
    assert updated.active_organization == "Municipalidad de Santiago"
    assert updated.active_market_category == "Equipos Médicos"
    assert updated.active_time_range["year"] == 2024
    assert len(updated.referenced_entities) == 2
    assert updated.referenced_entities[0]["ordinal"] == 1
    assert updated.referenced_entities[0]["name"] == "Tecnomed Chile SpA"


def test_get_prompt_messages_sliding_window_and_summary():
    manager = ConversationMemoryManager(max_recent_turns=3)

    # 5 messages in history
    history = [
        ChatMessage(role=MessageRole.USER, content=f"Mensaje {i}")
        for i in range(1, 6)
    ]

    state = ConversationContextState(summary="Resumen de turnos previos sobre licitaciones.")

    pruned = manager.get_prompt_messages(history, state)

    # Injects 1 summary message + 3 most recent turns = 4 messages total
    assert len(pruned) == 4
    assert pruned[0].role == MessageRole.SYSTEM
    assert "Resumen de turnos previos" in pruned[0].content
    assert pruned[1].content == "Mensaje 3"
    assert pruned[2].content == "Mensaje 4"
    assert pruned[3].content == "Mensaje 5"
