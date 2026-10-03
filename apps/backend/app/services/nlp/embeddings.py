"""Embedding application service (Fase 6.18)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import numpy as np

from app.ml.embeddings import EmbeddingService as BaseEmbeddingService
from app.nlp.semantic import cosine_similarity
from app.repositories.knowledge import EmbeddingRepository

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(
        self,
        base_service: BaseEmbeddingService | None = None,
        model: "SentenceTransformer | None" = None,
        embedding_repository: EmbeddingRepository | None = None,
    ) -> None:
        self._base = base_service or BaseEmbeddingService(model=model)
        self._repo = embedding_repository

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        return self._base.encode(texts)

    def compute_similarity(self, vector_a: np.ndarray, vector_b: np.ndarray) -> float:
        return cosine_similarity(vector_a, vector_b)
