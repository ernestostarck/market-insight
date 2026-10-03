"""Unit tests for SemanticRetriever with pgvector (Fase 9.7).

Tests query vector embedding generation, pgvector similarity search integration,
metadata filtering, and traceability toward public procurement sources.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.ai.contracts import IntentType, QueryPlan, RetrievalStrategy
from app.ai.interfaces import Retriever
from app.ai.semantic_retriever import SemanticRetriever
from app.ml.embeddings import EmbeddingService as MLEmbeddingService
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository


@pytest.fixture
def mock_vector_repo() -> AsyncMock:
    repo = AsyncMock(spec=VectorSearchRepository)
    repo.search_by_vector = AsyncMock()
    return repo


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    service = MagicMock(spec=MLEmbeddingService)
    # Return dummy 384-dimensional normalized vector
    dummy_vec = np.ones((1, 384), dtype=np.float32)
    service.encode.return_value = dummy_vec
    return service


@pytest.fixture
def retriever(mock_vector_repo: AsyncMock, mock_embedding_service: MagicMock) -> SemanticRetriever:
    return SemanticRetriever(
        vector_repository=mock_vector_repo,
        embedding_service=mock_embedding_service,
        default_top_k=5,
        default_min_similarity=0.30,
    )


def test_semantic_retriever_satisfies_protocol(retriever: SemanticRetriever) -> None:
    assert isinstance(retriever, Retriever)


@pytest.mark.asyncio
async def test_semantic_retrieve_generates_vector_and_queries_pgvector(
    retriever: SemanticRetriever,
    mock_vector_repo: AsyncMock,
    mock_embedding_service: MagicMock,
) -> None:
    # Setup simulated vector search results
    sim1 = SimilarLicitacion(
        licitacion_id=105822,
        nombre="Adquisición de Sillas de Ruedas Eléctricas",
        similarity=0.8950,
        category_id=10,
        subcategory_id=101,
    )
    sim2 = SimilarLicitacion(
        licitacion_id=105823,
        nombre="Suministro de Andadores y Bastones",
        similarity=0.7820,
        category_id=10,
        subcategory_id=102,
    )
    mock_vector_repo.search_by_vector.return_value = [sim1, sim2]

    plan = QueryPlan(
        intent=IntentType.SEMANTIC_SEARCH,
        retrieval_strategy=RetrievalStrategy.SEMANTIC,
        semantic_query="equipamiento para movilidad asistida",
        filters={"category_code": "SALUD"},
        parameters={"top_k": 5, "min_similarity": 0.50},
    )

    result = await retriever.retrieve(plan)

    # 1. Verify embedding service call
    mock_embedding_service.encode.assert_called_once_with(["equipamiento para movilidad asistida"])

    # 2. Verify pgvector search call
    mock_vector_repo.search_by_vector.assert_called_once()
    call_kwargs = mock_vector_repo.search_by_vector.call_args[1]
    assert call_kwargs["top_k"] == 5
    assert call_kwargs["min_similarity"] == 0.50
    assert call_kwargs["category_code"] == "SALUD"

    # 3. Verify RetrievalResult structure
    assert result.strategy_used == RetrievalStrategy.SEMANTIC
    assert result.total_results == 2
    assert len(result.items) == 2
    assert len(result.sources) == 2
    assert result.execution_time_ms >= 0.0

    # 4. Verify Source traceability to Mercado Público
    source_1 = result.sources[0]
    assert source_1.id == "105822"
    assert source_1.source_type == "tender"
    assert source_1.title == "Adquisición de Sillas de Ruedas Eléctricas"
    assert source_1.url == "https://mercadopublico.cl/tender/105822"
    assert source_1.score == 0.8950
    assert "89.50%" in (source_1.snippet or "")

    source_2 = result.sources[1]
    assert source_2.id == "105823"
    assert source_2.score == 0.7820
    assert source_2.url == "https://mercadopublico.cl/tender/105823"
