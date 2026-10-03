"""Follow-up Question Resolution & Context Disambiguation for MercadoInsight AI (Fase 9.19).

Resolves anaphoric expressions ("el primero", "ese proveedor", "el año anterior"),
maintains active filters with delta updates, detects topic shifts, and prompts for clarification
when genuine ambiguity exists.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.ai.memory import ConversationContextState

_ORDINAL_MAP = {
    "primero": 1,
    "primera": 1,
    "1ro": 1,
    "1ra": 1,
    "segundo": 2,
    "segunda": 2,
    "2do": 2,
    "2da": 2,
    "tercero": 3,
    "tercera": 3,
    "3ro": 3,
    "3ra": 3,
    "cuarto": 4,
    "cuarta": 4,
    "quinto": 5,
    "quinta": 5,
}

_YEAR_DELTA_REGEX = re.compile(
    r"^(?:¿?\s*y\s+(?:en|para)\s+(?:el\s+año\s+)?(20\d{2})\??|¿?\s*y\s+el\s+año\s+anterior\??)$",
    re.IGNORECASE,
)


class FollowUpResolution(BaseModel):
    """Result of resolving anaphoric references and merging contextual state."""

    resolved_query: str = Field(..., description="Self-contained enriched user query.")
    merged_filters: dict[str, Any] = Field(default_factory=dict, description="Active inherited and delta filters.")
    resolved_entity: dict[str, Any] | None = Field(default=None, description="Entity identified from reference.")
    is_follow_up: bool = Field(default=False, description="True if query depended on prior context.")
    is_topic_shift: bool = Field(default=False, description="True if user changed subject.")
    needs_clarification: bool = Field(default=False, description="True if reference is ambiguous.")
    clarification_message: str | None = Field(default=None, description="Prompt asking user to disambiguate.")


class FollowUpResolver:
    """Disambiguates follow-up questions using prior conversation context state."""

    def resolve(
        self,
        query: str,
        state: ConversationContextState,
    ) -> FollowUpResolution:
        """Resolve anaphoras, apply delta filters, and detect topic shifts."""
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # If there is no prior context history, return query as-is
        if state.turn_count == 0:
            return FollowUpResolution(resolved_query=q_clean, merged_filters={})

        # 1. Delta Year Modification (e.g. "¿Y en 2024?" or "¿Y el año anterior?")
        year_match = _YEAR_DELTA_REGEX.match(q_lower)
        if year_match:
            target_year: int
            if "anterior" in q_lower:
                prev_year = int(state.active_time_range.get("year", 2025))
                target_year = prev_year - 1
            else:
                target_year = int(year_match.group(1))

            merged_filters = dict(state.active_filters)
            merged_filters["year"] = target_year

            subject = state.active_organization or state.active_supplier or state.active_market_category or "compras públicas"
            resolved_query = f"¿Cuánto fue el gasto para {subject} en el año {target_year}?"

            return FollowUpResolution(
                resolved_query=resolved_query,
                merged_filters=merged_filters,
                is_follow_up=True,
            )

        # 2. Ordinal Resolution ("el primero", "el segundo", "el último")
        for ord_word, ord_idx in _ORDINAL_MAP.items():
            if re.search(rf"\b(?:el|la)\s+{ord_word}\b", q_lower) and 0 <= ord_idx - 1 < len(state.referenced_entities):
                target_ent = state.referenced_entities[ord_idx - 1]
                ent_name = target_ent.get("name", "")
                ent_type = target_ent.get("type", "entity")

                # Rewrite query substituting ordinal with entity name
                resolved_query = re.sub(
                    rf"\b(?:el|la)\s+{ord_word}\b",
                    ent_name,
                    q_clean,
                    flags=re.IGNORECASE,
                )
                merged_filters = dict(state.active_filters)
                if ent_type in ("supplier", "proveedor"):
                    merged_filters["proveedor_razon_social"] = ent_name
                elif ent_type in ("organization", "organismo", "buyer"):
                    merged_filters["comprador_nombre"] = ent_name

                return FollowUpResolution(
                    resolved_query=resolved_query,
                    merged_filters=merged_filters,
                    resolved_entity=target_ent,
                    is_follow_up=True,
                )

        if re.search(r"\b(?:el|la)\s+últim[oa]\b", q_lower) and state.referenced_entities:
            target_ent = state.referenced_entities[-1]
            ent_name = target_ent.get("name", "")
            ent_type = target_ent.get("type", "entity")

            resolved_query = re.sub(
                r"\b(?:el|la)\s+últim[oa]\b",
                ent_name,
                q_clean,
                flags=re.IGNORECASE,
            )
            merged_filters = dict(state.active_filters)
            if ent_type in ("supplier", "proveedor"):
                merged_filters["proveedor_razon_social"] = ent_name
            elif ent_type in ("organization", "organismo", "buyer"):
                merged_filters["comprador_nombre"] = ent_name

            return FollowUpResolution(
                resolved_query=resolved_query,
                merged_filters=merged_filters,
                resolved_entity=target_ent,
                is_follow_up=True,
            )

        # 3. Demonstrative Pronoun Resolution ("ese proveedor", "esa municipalidad", "ese hospital")
        if (
            re.search(r"\b(?:ese|dicho|aquel)\s+proveedor\b|\b(?:esa|dicha)\s+empresa\b", q_lower)
            and state.active_supplier
        ):
            resolved_query = re.sub(
                r"\b(?:ese|dicho|aquel)\s+proveedor\b|\b(?:esa|dicha)\s+empresa\b",
                state.active_supplier,
                q_clean,
                flags=re.IGNORECASE,
            )
            merged_filters = dict(state.active_filters)
            merged_filters["proveedor_razon_social"] = state.active_supplier
            return FollowUpResolution(
                resolved_query=resolved_query,
                merged_filters=merged_filters,
                resolved_entity={"name": state.active_supplier, "type": "supplier"},
                is_follow_up=True,
            )

        if (
            re.search(r"\b(?:esa|dicha)\s+municipalidad\b|\b(?:ese|dicho)\s+hospital\b|\b(?:ese|dicho)\s+organismo\b", q_lower)
            and state.active_organization
        ):
            resolved_query = re.sub(
                r"\b(?:esa|dicha)\s+municipalidad\b|\b(?:ese|dicho)\s+hospital\b|\b(?:ese|dicho)\s+organismo\b",
                state.active_organization,
                q_clean,
                flags=re.IGNORECASE,
            )
            merged_filters = dict(state.active_filters)
            merged_filters["comprador_nombre"] = state.active_organization
            return FollowUpResolution(
                resolved_query=resolved_query,
                merged_filters=merged_filters,
                resolved_entity={"name": state.active_organization, "type": "organization"},
                is_follow_up=True,
            )

        # 4. Ambiguity Detection: Short follow-up without clear target when multiple entities exist
        if (
            re.search(r"^¿?\s*(?:cuánto|cuanto)\s+(?:vendió|gasto|facturó|adjudicó)\??$", q_lower)
            and len(state.referenced_entities) > 1
        ):
                names = [e.get("name", f"Entidad {i+1}") for i, e in enumerate(state.referenced_entities)]
                msg = (
                    f"¿A cuál de las entidades te refieres? Puedes indicar el nombre o número: "
                    f"{', '.join(f'{i+1}. {n}' for i, n in enumerate(names))}."
                )
                return FollowUpResolution(
                    resolved_query=q_clean,
                    merged_filters=state.active_filters,
                    is_follow_up=True,
                    needs_clarification=True,
                    clarification_message=msg,
                )

        # 5. Default: Pass query through, retaining existing filters as context baseline
        return FollowUpResolution(
            resolved_query=q_clean,
            merged_filters=dict(state.active_filters),
            is_follow_up=False,
        )
