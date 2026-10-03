"""Build embedding vectors for taxonomy nodes (concepts, categories) once,
in memory — never persisted (see docs/07-ai/pgvector.md and
docs/07-ai/semantic-classification.md for why). Shared by
`EmbeddingsStageExecutor` (worker, per-run scoring against concepts) and
callers of `VectorSearchRepository.search_by_concept`/`search_by_category`
(6.9) — both need the same "concept/category -> vector" mapping, built
exactly once per process rather than re-embedded per call, since
`EmbeddingService.encode()` is a real (CPU-bound) model inference call and
`docs/07-ai/architecture.md` rules out inference in a per-request path."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.ml.embeddings import EmbeddingService
from app.nlp.taxonomy import DomainConcept, Taxonomy


@dataclass(frozen=True, slots=True)
class ConceptVector:
    concept: DomainConcept
    category_code: str
    subcategory_code: str
    vector: np.ndarray


@dataclass(frozen=True, slots=True)
class CategoryVector:
    category_code: str
    vector: np.ndarray


def build_concept_vectors(taxonomy: Taxonomy, embedding_service: EmbeddingService) -> tuple[ConceptVector, ...]:
    entries = [
        (category.code, subcategory.code, concept)
        for category in taxonomy.categories
        for subcategory in category.subcategories
        for concept in subcategory.concepts
    ]
    if not entries:
        return ()
    texts = [f"{concept.name}. {concept.description}" for _, _, concept in entries]
    vectors = embedding_service.encode(texts)
    return tuple(
        ConceptVector(concept=concept, category_code=category_code, subcategory_code=subcategory_code, vector=vectors[i])
        for i, (category_code, subcategory_code, concept) in enumerate(entries)
    )


def build_category_vectors(taxonomy: Taxonomy, embedding_service: EmbeddingService) -> tuple[CategoryVector, ...]:
    categories = list(taxonomy.categories)
    if not categories:
        return ()
    texts = [f"{category.name}. {category.description}" for category in categories]
    vectors = embedding_service.encode(texts)
    return tuple(
        CategoryVector(category_code=category.code, vector=vectors[i])
        for i, category in enumerate(categories)
    )
