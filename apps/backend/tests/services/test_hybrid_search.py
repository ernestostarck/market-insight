import numpy as np

from app.repositories.hybrid_search import TextMatch
from app.repositories.vector_search import SimilarLicitacion
from app.services.hybrid_search import HybridSearchService
from app.nlp.taxonomy import DomainConcept, Taxonomy, TaxonomyCategory, TaxonomySubcategory


class FakeHybridRepository:
    def __init__(self, fulltext=(), products=(), by_code=()) -> None:
        self._fulltext = list(fulltext)
        self._products = list(products)
        self._by_code = list(by_code)
        self.fulltext_calls: list[str] = []

    async def search_fulltext(self, query: str, *, limit: int = 20):
        self.fulltext_calls.append(query)
        return self._fulltext[:limit]

    async def search_products(self, query: str, *, limit: int = 20):
        return self._products[:limit]

    async def search_by_code(self, code: str, *, limit: int = 20):
        return self._by_code[:limit]


class FakeVectorRepository:
    def __init__(self, semantic=()) -> None:
        self._semantic = list(semantic)
        self.search_by_vector_calls = 0
        self.concept_calls: list[str] = []
        self.category_calls: list[str] = []

    async def search_by_vector(self, vector, *, top_k=10, min_similarity=0.0, exclude_licitacion_id=None, category_code=None):
        self.search_by_vector_calls += 1
        return self._semantic[:top_k]

    async def search_by_concept(self, concept_code, concept_vectors, *, top_k=10, min_similarity=0.0):
        self.concept_calls.append(concept_code)
        return self._semantic[:top_k]

    async def search_by_category(self, category_code, category_vectors, *, top_k=10, min_similarity=0.0):
        self.category_calls.append(category_code)
        return self._semantic[:top_k]


class FakeEmbeddingService:
    MODEL_NAME = "fake-model"

    def __init__(self) -> None:
        self.encode_calls: list[list[str]] = []

    def encode(self, texts):
        texts = list(texts)
        self.encode_calls.append(texts)
        return np.zeros((len(texts), 2), dtype=np.float32)


def _taxonomy() -> Taxonomy:
    return Taxonomy(
        version="taxonomy-test",
        categories=(
            TaxonomyCategory(
                code="health", name="Salud", description="Salud",
                subcategories=(
                    TaxonomySubcategory(
                        code="geriatric-care", name="Geriatria", description="Geriatria",
                        concepts=(DomainConcept("geriatria", "Geriatria", "Atencion geriatrica"),),
                    ),
                ),
            ),
        ),
    )


def _service(hybrid_repo=None, vector_repo=None, embedding=None) -> tuple[HybridSearchService, FakeEmbeddingService]:
    embedding = embedding or FakeEmbeddingService()
    service = HybridSearchService(
        hybrid_repo or FakeHybridRepository(), vector_repo or FakeVectorRepository(), embedding, taxonomy=_taxonomy(),
    )
    return service, embedding


async def test_search_ranks_docs_found_by_both_lists_above_single_list_matches() -> None:
    fulltext = [
        TextMatch(licitacion_id=1, nombre="Ambos", codigo="C1", rank=5.0),
        TextMatch(licitacion_id=2, nombre="Solo texto", codigo="C2", rank=3.0),
    ]
    semantic = [
        SimilarLicitacion(licitacion_id=1, nombre="Ambos", similarity=0.9, category_id=None, subcategory_id=None),
        SimilarLicitacion(licitacion_id=3, nombre="Solo semantico", similarity=0.8, category_id=None, subcategory_id=None),
    ]
    service, _ = _service(FakeHybridRepository(fulltext=fulltext), FakeVectorRepository(semantic=semantic))

    results = await service.search("silla de ruedas", top_k=10)

    assert results[0].licitacion_id == 1
    assert results[0].matched_via == frozenset({"fulltext", "semantic"})
    remaining_ids = {r.licitacion_id for r in results[1:]}
    assert remaining_ids == {2, 3}


async def test_search_respects_top_k() -> None:
    fulltext = [TextMatch(licitacion_id=i, nombre=f"Lic {i}", codigo=None, rank=float(i)) for i in range(5)]
    service, _ = _service(FakeHybridRepository(fulltext=fulltext))

    results = await service.search("query", top_k=2)

    assert len(results) == 2


async def test_search_embeds_the_query_text() -> None:
    service, embedding = _service()

    await service.search("silla de ruedas")

    assert ["silla de ruedas"] in embedding.encode_calls


async def test_search_by_code_is_a_passthrough() -> None:
    matches = [TextMatch(licitacion_id=1, nombre="Lic", codigo="ABC-1", rank=1.0)]
    repo = FakeHybridRepository(by_code=matches)
    service, _ = _service(repo)

    results = await service.search_by_code("ABC-1")

    assert results == matches


async def test_search_by_concept_reuses_precomputed_vectors() -> None:
    embedding = FakeEmbeddingService()
    vector_repo = FakeVectorRepository()
    service, _ = _service(vector_repo=vector_repo, embedding=embedding)
    calls_after_init = len(embedding.encode_calls)

    await service.search_by_concept("geriatria")

    assert vector_repo.concept_calls == ["geriatria"]
    assert len(embedding.encode_calls) == calls_after_init  # no new encode() call — vectors were built once in __init__
