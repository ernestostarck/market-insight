"""Validation package for Phase 6 (NLP & Knowledge Layer) on real Mercado Público data."""

from __future__ import annotations

from app.nlp.validation.dataset import RealTender, get_validation_tenders
from app.nlp.validation.validator import RealMarketPublicoValidator, ValidationSummary

__all__ = [
    "RealTender",
    "RealMarketPublicoValidator",
    "ValidationSummary",
    "get_validation_tenders",
]
