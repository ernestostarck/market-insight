"""Citation extraction, verification, and navigation routing for MercadoInsight AI (Fase 9.14).

Extracts source citations from generated answers, binds them to verified retrieval evidence,
detects fictitious citations, and assigns SPA deep-links.
"""

from __future__ import annotations

import re

from app.ai.contracts import Citation, Source

# Pattern matching "[Fuente: {tipo} {id}]" or "[Fuente #{num}]" or "[Fuente: {id}]"
_CITATION_REGEX = re.compile(
    r"\[Fuente(?:\s*#(?P<num>\d+)|\s*:\s*(?:(?P<type>[\w_]+)\s+)?(?P<id>[^\]\n]+))\]",
    re.IGNORECASE,
)


class CitationManager:
    """Extracts, verifies, and routes citations referencing public procurement evidence."""

    @staticmethod
    def build_target_route(source_type: str, entity_id: str) -> str:
        """Construct frontend SPA navigation route for the referenced record."""
        st = source_type.lower()
        clean_id = entity_id.strip()

        if st in ("tender", "licitacion"):
            return f"/licitaciones/{clean_id}"
        if st in ("purchase_order", "orden_compra", "oc"):
            return f"/ordenes-compra/{clean_id}"
        if st in ("supplier", "proveedor"):
            return f"/proveedores/{clean_id}"
        if st in ("buyer", "comprador", "organismo"):
            return f"/organismos/{clean_id}"
        if st in ("mart", "analytics", "sql"):
            return "/analytics"
        return f"/search?q={clean_id}"

    def extract_citations(
        self,
        text: str,
        context_sources: list[Source],
    ) -> list[Citation]:
        """Extract citations from text and verify each against available context sources."""
        citations: list[Citation] = []
        sources_by_id: dict[str, Source] = {
            s.id.strip().lower(): s for s in context_sources
        }

        # Track citation index
        cit_counter = 1
        seen_citations: set[str] = set()

        for match in _CITATION_REGEX.finditer(text):
            num_group = match.group("num")
            type_group = match.group("type")
            id_group = match.group("id")

            matched_source: Source | None = None
            resolved_id: str = ""
            resolved_type: str = type_group or "tender"

            if num_group is not None:
                # 1-based index into sources
                idx = int(num_group) - 1
                if 0 <= idx < len(context_sources):
                    matched_source = context_sources[idx]
                    resolved_id = matched_source.id
                    resolved_type = matched_source.source_type
                else:
                    resolved_id = f"num-{num_group}"
            elif id_group is not None:
                raw_id = id_group.strip()
                resolved_id = raw_id
                # Check exact or normalized ID match
                norm_id = raw_id.lower()
                if norm_id in sources_by_id:
                    matched_source = sources_by_id[norm_id]
                    resolved_type = matched_source.source_type
                else:
                    # Partial match on source title or ID
                    for src in context_sources:
                        if (
                            raw_id in src.id
                            or src.id in raw_id
                            or (src.title and raw_id.lower() in src.title.lower())
                        ):
                            matched_source = src
                            resolved_type = src.source_type
                            resolved_id = src.id
                            break

            citation_key = f"{resolved_type}:{resolved_id}"
            if citation_key in seen_citations:
                continue
            seen_citations.add(citation_key)

            # Find claim sentence context around the match
            start_pos = max(0, match.start() - 120)
            end_pos = min(len(text), match.end() + 60)
            claim_snippet = text[start_pos:end_pos].replace("\n", " ").strip()

            if matched_source is not None:
                route = self.build_target_route(matched_source.source_type, matched_source.id)
                citation = Citation(
                    id=f"cit-{cit_counter}",
                    source_id=matched_source.id,
                    source_type=matched_source.source_type,
                    title=matched_source.title,
                    snippet=matched_source.snippet,
                    relevance=matched_source.score,
                    url=matched_source.url,
                    claim_text=claim_snippet,
                    target_route=route,
                    is_verified=True,
                )
            else:
                # Fictitious or unverified citation
                route = self.build_target_route(resolved_type, resolved_id)
                citation = Citation(
                    id=f"cit-{cit_counter}",
                    source_id=resolved_id,
                    source_type=resolved_type,
                    title=f"Referencia no verificada: {resolved_id}",
                    claim_text=claim_snippet,
                    target_route=route,
                    is_verified=False,
                )

            citations.append(citation)
            cit_counter += 1

        # If no explicit tags were extracted but context sources exist, bind top context sources
        if not citations and context_sources:
            for idx, src in enumerate(context_sources[:5], start=1):
                route = self.build_target_route(src.source_type, src.id)
                citations.append(
                    Citation(
                        id=f"cit-{idx}",
                        source_id=src.id,
                        source_type=src.source_type,
                        title=src.title,
                        snippet=src.snippet,
                        relevance=src.score,
                        url=src.url,
                        target_route=route,
                        is_verified=True,
                    )
                )

        return citations

    @staticmethod
    def get_fictitious_citations(citations: list[Citation]) -> list[Citation]:
        """Return any citations detected as unverified / without backing evidence."""
        return [c for c in citations if not c.is_verified]
