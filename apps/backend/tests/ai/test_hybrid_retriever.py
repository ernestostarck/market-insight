"""Unit tests for HybridRetriever (Fase 9.8)."""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.ai.contracts import IntentType, QueryPlan, RetrievalStrategy
from app.ai.hybrid_retriever import HybridRetriever
from app.ai.interfaces import Retriever
from app.ml.embeddings import EmbeddingService as MLEmbeddingService
from app.repositories.hybrid_search import HybridSearchRepository, TextMatch
from app.repositories.vector_search import SimilarLicitacion, VectorSearchRepository


@pytest.fixture
def mock_hybrid_repo() -> AsyncMock:
    repo = AsyncMock(spec=HybridSearchRepository)
    repo.search_fulltext = AsyncMock()
    return repo


@pytest.fixture
def mock_vector_repo() -> AsyncMock:
    repo = AsyncMock(spec=VectorSearchRepository)
    repo.search_by_vector = AsyncMock()
    return repo


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    service = MagicMock(spec=MLEmbeddingService)
    service.encode.return_value = np.ones((1, 384), dtype=np.float32)
    return service


@pytest.fixture
def hybrid_retriever(
    mock_hybrid_repo: AsyncMock,
    mock_vector_repo: AsyncMock,
    mock_embedding_service: MagicMock,
) -> HybridRetriever:
    return HybridRetriever(
        hybrid_repo=mock_hybrid_repo,
        vector_repo=mock_vector_repo,
        embedding_service=mock_embedding_service,
        default_top_k=5,
    )


def test_hybrid_retriever_satisfies_protocol(hybrid_retriever: HybridRetriever) -> None:
    assert isinstance(hybrid_retriever, Retriever)


@pytest.mark.asyncio
async def test_hybrid_retriever_combines_and_deduplicates(
    hybrid_retriever: HybridRetriever,
    mock_hybrid_repo: AsyncMock,
    mock_vector_repo: AsyncMock,
) -> None:
    # Full-text matches: lic 101 and 102
    mock_hybrid_repo.search_fulltext.return_value = [
        TextMatch(licitacion_id=101, codigo="101-LP24", nombre="Ambulancias 4x4", rank=0.85),
        TextMatch(licitacion_id=102, codigo="102-LP24", nombre="Camillas Hospitalarias", rank=0.40),
    ]

    # Vector matches: lic 101 (overlap) and 103
    mock_vector_repo.search_by_vector.return_value = [
        SimilarLicitacion(
            licitacion_id=101,
            similarity=0.92,
            nombre="Ambulancias 4x4",
            category_id=10,
            subcategory_id=20,
        ),
        SimilarLicitacion(
            licitacion_id=103,
            similarity=0.75,
            nombre="Equipos Desfibriladores",
            category_id=10,
            subcategory_id=21,
        ),
    ]

    plan = QueryPlan(
        intent=IntentType.SEARCH,
        retrieval_strategy=RetrievalStrategy.HYBRID,
        semantic_query="ambulancias y equipamiento medico",
        filters={"category_code": "CAT-MED"},
        parameters={"top_k": 5},
    )

    result = await hybrid_retriever.retrieve(plan)

    assert result.strategy_used == RetrievalStrategy.HYBRID
    assert result.total_results == 3
    assert len(result.items) == 3
    assert len(result.sources) == 3

    # Top item should be 101 because it has both fulltext and semantic match (synergy boost)
    top_item = result.items[0]
    assert top_item["licitacion_id"] == 101
    assert "fulltext" in top_item["matched_via"]
    assert "semantic" in top_item["matched_via"]
    assert top_item["hybrid_score"] > result.items[1]["hybrid_score"]

    # Verify calls
    mock_hybrid_repo.search_fulltext.assert_awaited_once_with("ambulancias y equipamiento medico", limit=15)
    mock_vector_repo.search_by_vector.assert_awaited_once()


@pytest.mark.asyncio
async def test_hybrid_retriever_handles_empty_matches(
    hybrid_retriever: HybridRetriever,
    mock_hybrid_repo: AsyncMock,
    mock_vector_repo: AsyncMock,
) -> None:
    mock_hybrid_repo.search_fulltext.return_value = []
    mock_vector_repo.search_by_vector.return_value = []

    plan = QueryPlan(
        intent=IntentType.SEARCH,
        retrieval_strategy=RetrievalStrategy.HYBRID,
        semantic_query="consulta sin coincidencias",
    )

    result = await hybrid_retriever.retrieve(plan)

    assert result.total_results == 0
    assert result.items == []
    assert result.sources == []
