import numpy as np
import pytest

from app.ml.embeddings import EmbeddingService
from app.nlp.semantic import cosine_similarity


@pytest.mark.slow
def test_encode_returns_384_dim_unit_vectors_matching_the_model_used_elsewhere() -> None:
    service = EmbeddingService()

    vectors = service.encode(["silla de ruedas para adulto mayor"])

    assert vectors.shape == (1, EmbeddingService.DIMENSIONS)
    assert np.isclose(np.linalg.norm(vectors[0]), 1.0, atol=1e-4)


@pytest.mark.slow
def test_encode_ranks_semantically_related_spanish_text_above_unrelated_text() -> None:
    service = EmbeddingService()

    anchor, related, unrelated = service.encode([
        "adquisicion de sillas de ruedas para personas con discapacidad",
        "compra de ayudas tecnicas para movilidad reducida",
        "compra de notebooks y licencias de office para la oficina",
    ])

    assert cosine_similarity(anchor, related) > cosine_similarity(anchor, unrelated)


def test_encode_returns_empty_array_for_no_texts() -> None:
    service = EmbeddingService()

    vectors = service.encode([])

    assert vectors.shape == (0, EmbeddingService.DIMENSIONS)
