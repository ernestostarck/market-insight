from app.models import (
    Category, Chunk, Classification, Concept, DatasetVersion, Document, Embedding, Entity,
    HumanReview, Keyword, ModelVersion, Product, ProductConcept, Relationship, Rule, Subcategory,
)
from app.models.knowledge import Vector
from app.nlp.contracts import ModelLifecycleState


def test_knowledge_model_registers_all_phase_6_tables() -> None:
    tables = {
        Category.__table__, Subcategory.__table__, Concept.__table__, Keyword.__table__,
        Rule.__table__, Embedding.__table__, Classification.__table__, Entity.__table__,
        Relationship.__table__, HumanReview.__table__, ModelVersion.__table__,
        DatasetVersion.__table__, Document.__table__, Chunk.__table__,
        ProductConcept.__table__, Product.__table__,
    }
    assert {table.schema for table in tables} == {"knowledge"}
    assert {table.name for table in tables} == {
        "categories", "subcategories", "concepts", "keywords", "rules", "embeddings",
        "classifications", "entities", "relationships", "human_reviews", "model_versions",
        "dataset_versions", "documents", "chunks", "product_concepts", "products",
    }


def test_product_concept_is_scoped_by_category_subcategory_and_dictionary_version() -> None:
    assert {fk.target_fullname for fk in ProductConcept.__table__.foreign_keys} == {
        "knowledge.categories.id", "knowledge.subcategories.id",
    }
    assert "uq_knowledge_product_concepts_code_version" in {
        constraint.name for constraint in ProductConcept.__table__.constraints
    }


def test_product_links_item_to_product_concept_with_attributes() -> None:
    columns = Product.__table__.columns
    assert {
        "licitacion_item_id", "product_concept_id", "cantidad", "unidad",
        "materiales", "dimensiones", "capacidad", "caracteristicas_tecnicas", "confidence_score",
    } <= set(columns.keys())
    fk_targets = {fk.target_fullname for fk in Product.__table__.foreign_keys}
    assert fk_targets == {
        "core.licitacion.id", "core.licitacion_item.id",
        "knowledge.product_concepts.id", "knowledge.classifications.id",
    }
    assert "uq_knowledge_products_item_concept" in {
        constraint.name for constraint in Product.__table__.constraints
    }


def test_concept_is_third_taxonomy_level_scoped_by_subcategory_and_version() -> None:
    assert {fk.target_fullname for fk in Concept.__table__.foreign_keys} == {"knowledge.subcategories.id"}
    assert "uq_knowledge_concepts_code_version" in {
        constraint.name for constraint in Concept.__table__.constraints
    }


def test_relationship_links_two_entities_scoped_by_licitacion() -> None:
    columns = Relationship.__table__.columns
    assert {"subject_entity_id", "predicate", "object_entity_id", "confidence_score"} <= set(columns.keys())
    fk_targets = [fk.target_fullname for fk in Relationship.__table__.foreign_keys]
    assert fk_targets.count("knowledge.entities.id") == 2
    assert "core.licitacion.id" in fk_targets


def test_document_is_scoped_by_licitacion_and_content_hash() -> None:
    assert {fk.target_fullname for fk in Document.__table__.foreign_keys} == {"core.licitacion.id"}
    assert "uq_knowledge_documents_licitacion_hash" in {
        constraint.name for constraint in Document.__table__.constraints
    }


def test_chunk_belongs_to_document_and_tracks_offsets() -> None:
    columns = Chunk.__table__.columns
    assert {"document_id", "sequence", "text", "start_offset", "end_offset"} <= set(columns.keys())
    assert {fk.target_fullname for fk in Chunk.__table__.foreign_keys} == {"knowledge.documents.id"}
    assert "uq_knowledge_chunks_document_sequence" in {
        constraint.name for constraint in Chunk.__table__.constraints
    }


def test_embeddings_are_linked_to_licitaciones_and_use_pgvector() -> None:
    embedding = Embedding.__table__
    assert isinstance(embedding.c.vector.type, Vector)
    assert embedding.c.vector.type.dimensions == 384
    assert {foreign_key.target_fullname for foreign_key in embedding.foreign_keys} == {
        "core.licitacion.id", "knowledge.model_versions.id"
    }


def test_classification_and_review_integrity_relationships_are_present() -> None:
    assert "uq_knowledge_reviews_classification_reviewer" in {
        constraint.name for constraint in HumanReview.__table__.constraints
    }
    assert {"relevant", "relevance_tier", "accepted", "reason"} <= set(HumanReview.__table__.columns.keys())
    assert {foreign_key.target_fullname for foreign_key in Classification.__table__.foreign_keys} >= {
        "core.licitacion.id", "knowledge.categories.id", "knowledge.dataset_versions.id"
    }


def test_keyword_is_scoped_by_taxonomy_and_dictionary_version() -> None:
    columns = Keyword.__table__.columns
    assert "taxonomy_version" in columns
    assert "dictionary_version" in columns
    scope_constraint = next(
        constraint for constraint in Keyword.__table__.constraints
        if constraint.name == "uq_knowledge_keywords_scope"
    )
    assert {column.name for column in scope_constraint.columns} == {
        "term", "category_id", "subcategory_id", "taxonomy_version", "dictionary_version",
    }


def test_model_version_default_status_matches_draft_lifecycle_state() -> None:
    assert ModelVersion.__table__.c.status.default.arg == ModelLifecycleState.DRAFT.value
