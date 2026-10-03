from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Wraps a sentence-transformers model. 384-dim, multilingual — matches
    `Vector(384)` (app/models/knowledge.py, fixed in 6.6). Lazily loaded so
    importing this module (e.g. in unit tests that inject a fake model)
    never requires network access or pays the model-load cost."""

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    DIMENSIONS = 384

    def __init__(self, model: "SentenceTransformer | None" = None) -> None:
        self._model = model

    def _get_model(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.empty((0, self.DIMENSIONS), dtype=np.float32)
        vectors = self._get_model().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)
