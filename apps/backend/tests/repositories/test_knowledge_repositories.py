import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.knowledge import (
    Category,
    Chunk,
    Classification,
    Concept,
    Document,
    Embedding,
    Entity,
    HumanReview,
    Keyword,
    ModelVersion,
    ProductConcept,
    Relationship,
    Subcategory,
)
from app.repositories.knowledge import (
    ChunkRepository,
    ClassificationRepository,
    ConceptRepository,
    DictionaryRepository,
    DocumentRepository,
    EmbeddingRepository,
    EntityRepository,
    HumanReviewRepository,
    ModelRepository,
    RelationshipRepository,
    TaxonomyRepository,
)


def _mock_session_with_result(scalars=()):
    session = AsyncMock()
    session.add = MagicMock()
    mock_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = list(scalars)
    scalars_mock.first.return_value = scalars[0] if scalars else None
    mock_result.scalars.return_value = scalars_mock
    mock_result.rowcount = len(scalars)
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_document_repository_crud() -> None:
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, licitacion_id=10, raw_text="raw", normalized_text="norm", language="es", content_hash="h1")
    session = _mock_session_with_result([doc])

    repo = DocumentRepository(session)
    fetched = await repo.get(doc_id)
    assert fetched is not None
    assert fetched.id == doc_id

    docs = await repo.get_by_licitacion_id(10)
    assert len(docs) == 1

    by_hash = await repo.get_by_content_hash(10, "h1")
    assert by_hash is not None

    created = await repo.create(doc)
    assert session.add.called
    assert session.flush.called
    assert created.id == doc_id


@pytest.mark.asyncio
async def test_chunk_repository() -> None:
    doc_id = uuid.uuid4()
    chunks = [
        Chunk(id=uuid.uuid4(), document_id=doc_id, sequence=1, text="c1", start_offset=0, end_offset=2),
        Chunk(id=uuid.uuid4(), document_id=doc_id, sequence=2, text="c2", start_offset=2, end_offset=4),
    ]
    session = _mock_session_with_result(chunks)

    repo = ChunkRepository(session)
    fetched = await repo.get(chunks[0].id)
    assert fetched is not None

    all_chunks = await repo.list_by_document(doc_id)
    assert len(all_chunks) == 2

    created = await repo.create_many(chunks)
    assert len(created) == 2
    assert session.flush.called


@pytest.mark.asyncio
async def test_entity_repository() -> None:
    e_id = uuid.uuid4()
    ent = Entity(id=e_id, licitacion_id=20, entity_type="brand", value="Acme", confidence_score=0.9)
    session = _mock_session_with_result([ent])

    repo = EntityRepository(session)
    fetched = await repo.get(e_id)
    assert fetched is not None

    items = await repo.list_by_licitacion(20, entity_type="brand")
    assert len(items) == 1

    created = await repo.create_many([ent])
    assert len(created) == 1

    count = await repo.delete_by_licitacion(20)
    assert count == 1


@pytest.mark.asyncio
async def test_concept_repository() -> None:
    c = Concept(id=1, subcategory_id=10, code="wheelchair", name="Silla de ruedas", taxonomy_version="2026.2")
    session = _mock_session_with_result([c])

    repo = ConceptRepository(session)
    fetched = await repo.get(1)
    assert fetched is not None

    by_code = await repo.get_by_code("wheelchair", taxonomy_version="2026.2")
    assert by_code is not None

    by_sub = await repo.list_by_subcategory(10)
    assert len(by_sub) == 1

    created = await repo.create(c)
    assert created.code == "wheelchair"


@pytest.mark.asyncio
async def test_classification_repository() -> None:
    cl_id = uuid.uuid4()
    cl = Classification(
        id=cl_id, licitacion_id=50, category_id=1, subcategory_id=2,
        taxonomy_version="2026.2", confidence_score=0.88, relevance_tier="high",
    )
    session = _mock_session_with_result([cl])

    repo = ClassificationRepository(session)
    fetched = await repo.get(cl_id)
    assert fetched is not None

    latest = await repo.get_latest_by_licitacion_id(50)
    assert latest is not None

    items = await repo.list(skip=0, limit=10, category_id=1, min_confidence=0.8, relevance_tier="high")
    assert len(items) == 1

    created = await repo.create(cl)
    assert created.id == cl_id

    updated = await repo.update(cl_id, confidence_score=0.95)
    assert updated is not None


@pytest.mark.asyncio
async def test_embedding_repository() -> None:
    emb_id = uuid.uuid4()
    emb = Embedding(
        id=emb_id, licitacion_id=60, model_version_id=uuid.uuid4(),
        content_hash="hash", text="sample", vector=[0.1] * 384,
    )
    session = _mock_session_with_result([emb])

    repo = EmbeddingRepository(session)
    fetched = await repo.get(emb_id)
    assert fetched is not None

    latest = await repo.get_latest_by_licitacion_id(60)
    assert latest is not None

    created = await repo.create(emb)
    assert created.id == emb_id


@pytest.mark.asyncio
async def test_relationship_repository() -> None:
    rel_id = uuid.uuid4()
    rel = Relationship(
        id=rel_id, licitacion_id=70, subject_entity_id=uuid.uuid4(),
        predicate="provides", object_entity_id=uuid.uuid4(), confidence_score=0.85,
    )
    session = _mock_session_with_result([rel])

    repo = RelationshipRepository(session)
    fetched = await repo.get(rel_id)
    assert fetched is not None

    items = await repo.list_by_licitacion(70)
    assert len(items) == 1

    created = await repo.create_many([rel])
    assert len(created) == 1


@pytest.mark.asyncio
async def test_taxonomy_repository() -> None:
    cat = Category(id=1, code="health", name="Salud", taxonomy_version="2026.2")
    sub = Subcategory(id=10, category_id=1, code="geriatric-care", name="Cuidado", taxonomy_version="2026.2")
    conc = Concept(id=100, subcategory_id=10, code="c1", name="Concept 1", taxonomy_version="2026.2")

    session = AsyncMock()
    # Mock multiple executes
    mock_res_cat = MagicMock()
    mock_res_cat.scalars.return_value.first.return_value = cat
    mock_res_cat.scalars.return_value.all.return_value = [cat]

    mock_res_sub = MagicMock()
    mock_res_sub.scalars.return_value.first.return_value = sub
    mock_res_sub.scalars.return_value.all.return_value = [sub]

    mock_res_conc = MagicMock()
    mock_res_conc.scalars.return_value.first.return_value = conc
    mock_res_conc.scalars.return_value.all.return_value = [conc]

    session.execute.side_effect = [mock_res_cat, mock_res_cat, mock_res_cat, mock_res_sub, mock_res_sub, mock_res_sub,
                                   mock_res_cat, mock_res_sub, mock_res_conc]

    repo = TaxonomyRepository(session)
    assert await repo.get_category_by_id(1) == cat
    assert await repo.get_category_by_code("health") == cat
    assert len(await repo.list_categories()) == 1

    assert await repo.get_subcategory_by_id(10) == sub
    assert await repo.get_subcategory_by_code(1, "geriatric-care") == sub
    assert len(await repo.list_subcategories()) == 1

    tree = await repo.get_full_tree("2026.2")
    assert len(tree) == 1
    assert tree[0]["code"] == "health"
    assert len(tree[0]["subcategories"]) == 1
    assert tree[0]["subcategories"][0]["code"] == "geriatric-care"


@pytest.mark.asyncio
async def test_dictionary_repository() -> None:
    kw = Keyword(id=1, term="silla de ruedas", category_id=1, dictionary_version="2026.1")
    pc = ProductConcept(id=2, code="wheelchair", category_id=1, subcategory_id=10, dictionary_version="2026.1")
    session = _mock_session_with_result([kw])

    repo = DictionaryRepository(session)
    assert await repo.get_keyword("silla de ruedas") == kw
    assert len(await repo.list_keywords()) == 1

    # Product concept
    session2 = _mock_session_with_result([pc])
    repo2 = DictionaryRepository(session2)
    assert await repo2.get_product_concept_by_code("wheelchair") == pc
    assert len(await repo2.list_product_concepts()) == 1

    created_kw = await repo2.create_keyword(kw)
    assert created_kw.term == "silla de ruedas"
    created_pc = await repo2.create_product_concept(pc)
    assert created_pc.code == "wheelchair"


@pytest.mark.asyncio
async def test_model_repository() -> None:
    mv = ModelVersion(
        id=uuid.uuid4(), name="tfidf-logreg", version="2026.2.1",
        kind="classifier", parameters={"algorithm": "logreg"}, metrics={},
        artifact_uri="minio://models/m1", status="production",
    )
    session = _mock_session_with_result([mv])

    repo = ModelRepository(session)
    assert await repo.get(mv.id) == mv
    assert await repo.get_by_version("tfidf-logreg", "2026.2.1") == mv
    assert await repo.get_active_model("classifier") == mv
    assert len(await repo.list_versions("classifier")) == 1

    created = await repo.create(mv)
    assert created.name == "tfidf-logreg"

    updated = await repo.update_status(mv.id, "retired")
    assert updated is not None


@pytest.mark.asyncio
async def test_human_review_repository() -> None:
    cl_id = uuid.uuid4()
    rev_user_id = uuid.uuid4()
    hr = HumanReview(
        id=uuid.uuid4(), classification_id=cl_id, reviewer_id=rev_user_id,
        accepted=True, relevant=True, relevance_tier="high", reason="Validado",
    )
    session = _mock_session_with_result([hr])

    repo = HumanReviewRepository(session)
    assert await repo.get(hr.id) == hr
    assert await repo.get_by_classification(cl_id) == hr
    assert len(await repo.list()) == 1

    review = await repo.create_or_update(
        classification_id=cl_id, reviewer_id=rev_user_id,
        accepted=True, relevant=True, relevance_tier="high", reason="Validado",
    )
    assert review.accepted is True
