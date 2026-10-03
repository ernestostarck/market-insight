import numpy as np

from app.nlp.taxonomy import load_initial_taxonomy
from app.nlp.taxonomy_vectors import build_category_vectors, build_concept_vectors


class FakeEmbeddingService:
    def encode(self, texts):
        return np.array([[float(len(t)), 0.0] for t in texts], dtype=np.float32)


def test_build_concept_vectors_covers_every_taxonomy_concept() -> None:
    taxonomy = load_initial_taxonomy()

    vectors = build_concept_vectors(taxonomy, FakeEmbeddingService())

    all_concept_codes = {
        concept.code
        for category in taxonomy.categories
        for subcategory in category.subcategories
        for concept in subcategory.concepts
    }
    assert {v.concept.code for v in vectors} == all_concept_codes
    assert len(vectors) == len(all_concept_codes)


def test_build_concept_vectors_tracks_the_right_category_and_subcategory() -> None:
    taxonomy = load_initial_taxonomy()

    vectors = build_concept_vectors(taxonomy, FakeEmbeddingService())

    for candidate in vectors:
        category, subcategory, concept = taxonomy.locate(candidate.concept.code)
        assert candidate.category_code == category.code
        assert candidate.subcategory_code == subcategory.code
        assert candidate.concept is concept


def test_build_category_vectors_covers_every_category() -> None:
    taxonomy = load_initial_taxonomy()

    vectors = build_category_vectors(taxonomy, FakeEmbeddingService())

    assert {v.category_code for v in vectors} == {c.code for c in taxonomy.categories}
    assert len(vectors) == len(taxonomy.categories)


def test_build_vectors_returns_empty_tuple_for_empty_taxonomy() -> None:
    from app.nlp.taxonomy import Taxonomy

    empty = Taxonomy(version="taxonomy-empty", categories=())

    assert build_concept_vectors(empty, FakeEmbeddingService()) == ()
    assert build_category_vectors(empty, FakeEmbeddingService()) == ()
