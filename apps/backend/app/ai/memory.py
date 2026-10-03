"""Layered Conversation Memory for MercadoInsight AI (Fase 9.18).

Maintains short-term message sliding window, persistent conversation summary,
and active conversational context state (filters, entities, time range, suppliers, buyers).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ai.contracts import ChatMessage, MessageRole


class ConversationContextState(BaseModel):
    """Persistent structured context state carried across conversational turns."""

    model_config = ConfigDict(frozen=False)

    active_filters: dict[str, Any] = Field(default_factory=dict, description="Active metadata filters.")
    active_time_range: dict[str, Any] = Field(default_factory=dict, description="Active temporal filters.")
    active_market_category: str | None = Field(default=None, description="Active product or service category.")
    active_organization: str | None = Field(default=None, description="Active purchasing organization (buyer).")
    active_supplier: str | None = Field(default=None, description="Active vendor/supplier.")
    referenced_entities: list[dict[str, Any]] = Field(
        default_factory=list, description="Ordered list of entities discussed in the last turn."
    )
    summary: str | None = Field(default=None, description="Condensed summary of past turns.")
    turn_count: int = Field(default=0, description="Total turns processed in this session.")


class ConversationMemoryManager:
    """Manages short-term window, entity memory, and summary condensation."""

    def __init__(
        self,
        max_recent_turns: int = 4,
        summary_threshold_turns: int = 6,
    ) -> None:
        self.max_recent_turns = max_recent_turns
        self.summary_threshold_turns = summary_threshold_turns

    def get_context_state(self, session_metadata: dict[str, Any] | None) -> ConversationContextState:
        """Extract or initialize context state from session metadata."""
        if not session_metadata or "context_state" not in session_metadata:
            return ConversationContextState()
        raw = session_metadata["context_state"]
        if isinstance(raw, dict):
            return ConversationContextState(**raw)
        return ConversationContextState()

    def persist_context_state(
        self,
        session_metadata: dict[str, Any],
        state: ConversationContextState,
    ) -> dict[str, Any]:
        """Serialize context state into session metadata."""
        updated = dict(session_metadata)
        updated["context_state"] = state.model_dump()
        return updated

    def update_context_state(
        self,
        current_state: ConversationContextState,
        query: str,
        detected_entities: list[dict[str, Any]] | None = None,
        query_filters: dict[str, Any] | None = None,
        assistant_content: str | None = None,
    ) -> ConversationContextState:
        """Update active context state with newly observed entities and filters."""
        state = current_state.model_copy(deep=True)
        state.turn_count += 1

        # 1. Update filters and time range
        if query_filters:
            for k, v in query_filters.items():
                if v is not None:
                    state.active_filters[k] = v
                    if k in ("year", "start_date", "end_date", "mes", "año"):
                        state.active_time_range[k] = v
                    elif k in ("category", "categoria", "codigo_categoria"):
                        state.active_market_category = str(v)
                    elif k in ("comprador", "comprador_nombre", "comprador_rut", "organismo"):
                        state.active_organization = str(v)
                    elif k in ("proveedor", "proveedor_razon_social", "proveedor_rut"):
                        state.active_supplier = str(v)

        # 2. Update entities from planner/intent detector
        if detected_entities:
            ordered_entities: list[dict[str, Any]] = []
            for idx, ent in enumerate(detected_entities, start=1):
                ent_type = ent.get("type", "entity")
                ent_val = ent.get("value") or ent.get("text", "")
                ordered_entities.append({
                    "ordinal": idx,
                    "type": ent_type,
                    "name": ent_val,
                })
                if ent_type in ("supplier", "proveedor") and not state.active_supplier:
                    state.active_supplier = str(ent_val)
                elif ent_type in ("organization", "organismo", "buyer") and not state.active_organization:
                    state.active_organization = str(ent_val)
                elif ent_type in ("category", "categoria") and not state.active_market_category:
                    state.active_market_category = str(ent_val)

            if ordered_entities:
                state.referenced_entities = ordered_entities

        # 3. Periodically update conversation summary to prevent sending full history indefinitely
        if state.turn_count >= self.summary_threshold_turns and not state.summary:
            state.summary = (
                f"Conversación sobre contrataciones públicas. "
                f"Categoría activa: {state.active_market_category or 'General'}. "
                f"Organización: {state.active_organization or 'Todas'}. "
                f"Proveedor: {state.active_supplier or 'Todos'}."
            )

        return state

    def get_prompt_messages(
        self,
        history: list[ChatMessage],
        state: ConversationContextState | None = None,
    ) -> list[ChatMessage]:
        """Prune history to sliding window and prepend summary if available."""
        if not history:
            return []

        # Keep only the last N messages
        recent = history[-self.max_recent_turns:]

        # If summary exists and we pruned older messages, inject summary message
        if state and state.summary and len(history) > self.max_recent_turns:
            summary_msg = ChatMessage(
                role=MessageRole.SYSTEM,
                content=f"[Resumen de turnos anteriores: {state.summary}]",
            )
            return [summary_msg, *recent]

        return recent
