"""Asynchronous repositories for the `knowledge` schema (Fase 6.19).

Provides async repository classes over SQLAlchemy AsyncSession for all 11 knowledge entities:
1. DocumentRepository
2. ChunkRepository
3. EntityRepository
4. ConceptRepository
5. ClassificationRepository
6. EmbeddingRepository
7. RelationshipRepository
8. TaxonomyRepository
9. DictionaryRepository
10. ModelRepository
11. HumanReviewRepository
"""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import (
    Category,
    Chunk,
    Classification,
    Concept,
    DatasetVersion,
    Document,
    Embedding,
    Entity,
    HumanReview,
    Keyword,
    ModelVersion,
    NLPJob,
    ProductConcept,
    Relationship,
    Subcategory,
)
from app.nlp.contracts import ModelLifecycleState, validate_model_transition


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, document_id: uuid.UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalars().first()

    async def get_by_licitacion_id(self, licitacion_id: int) -> list[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.licitacion_id == licitacion_id)
            .order_by(desc(Document.created_at))
        )
        return list(result.scalars().all())

    async def get_by_content_hash(self, licitacion_id: int, content_hash: str) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.licitacion_id == licitacion_id,
                Document.content_hash == content_hash,
            )
        )
        return result.scalars().first()

    async def create(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.flush()
        return document


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, chunk_id: uuid.UUID) -> Chunk | None:
        result = await self.session.execute(
            select(Chunk).where(Chunk.id == chunk_id)
        )
        return result.scalars().first()

    async def list_by_document(self, document_id: uuid.UUID) -> list[Chunk]:
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.sequence)
        )
        return list(result.scalars().all())

    async def create_many(self, chunks: Sequence[Chunk]) -> list[Chunk]:
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()
        return list(chunks)


class EntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> Entity | None:
        result = await self.session.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalars().first()

    async def list_by_licitacion(
        self, licitacion_id: int, entity_type: str | None = None
    ) -> list[Entity]:
        stmt = select(Entity).where(Entity.licitacion_id == licitacion_id)
        if entity_type is not None:
            stmt = stmt.where(Entity.entity_type == entity_type)
        stmt = stmt.order_by(Entity.start_offset.nulls_last(), Entity.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_many(self, entities: Sequence[Entity]) -> list[Entity]:
        for entity in entities:
            self.session.add(entity)
        await self.session.flush()
        return list(entities)

    async def delete_by_licitacion(self, licitacion_id: int) -> int:
        stmt = delete(Entity).where(Entity.licitacion_id == licitacion_id)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class ConceptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, concept_id: int) -> Concept | None:
        result = await self.session.execute(
            select(Concept).where(Concept.id == concept_id)
        )
        return result.scalars().first()

    async def get_by_code(
        self, code: str, taxonomy_version: str | None = None
    ) -> Concept | None:
        stmt = select(Concept).where(Concept.code == code)
        if taxonomy_version is not None:
            stmt = stmt.where(Concept.taxonomy_version == taxonomy_version)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_subcategory(self, subcategory_id: int) -> list[Concept]:
        result = await self.session.execute(
            select(Concept)
            .where(Concept.subcategory_id == subcategory_id)
            .order_by(Concept.code)
        )
        return list(result.scalars().all())

    async def create(self, concept: Concept) -> Concept:
        self.session.add(concept)
        await self.session.flush()
        return concept


class ClassificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, classification_id: uuid.UUID) -> Classification | None:
        result = await self.session.execute(
            select(Classification).where(Classification.id == classification_id)
        )
        return result.scalars().first()

    async def get_latest_by_licitacion_id(self, licitacion_id: int) -> Classification | None:
        result = await self.session.execute(
            select(Classification)
            .where(Classification.licitacion_id == licitacion_id)
            .order_by(desc(Classification.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        category_id: int | None = None,
        min_confidence: float | None = None,
        relevance_tier: str | None = None,
    ) -> list[Classification]:
        stmt = select(Classification)
        if category_id is not None:
            stmt = stmt.where(Classification.category_id == category_id)
        if min_confidence is not None:
            stmt = stmt.where(Classification.confidence_score >= min_confidence)
        if relevance_tier is not None:
            stmt = stmt.where(Classification.relevance_tier == relevance_tier)
        stmt = stmt.order_by(desc(Classification.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, classification: Classification) -> Classification:
        self.session.add(classification)
        await self.session.flush()
        return classification

    async def update(self, classification_id: uuid.UUID, **kwargs) -> Classification | None:
        if not kwargs:
            return await self.get(classification_id)
        await self.session.execute(
            update(Classification)
            .where(Classification.id == classification_id)
            .values(**kwargs)
        )
        await self.session.flush()
        return await self.get(classification_id)


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, embedding_id: uuid.UUID) -> Embedding | None:
        result = await self.session.execute(
            select(Embedding).where(Embedding.id == embedding_id)
        )
        return result.scalars().first()

    async def get_latest_by_licitacion_id(self, licitacion_id: int) -> Embedding | None:
        result = await self.session.execute(
            select(Embedding)
            .where(Embedding.licitacion_id == licitacion_id)
            .order_by(desc(Embedding.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def create(self, embedding: Embedding) -> Embedding:
        self.session.add(embedding)
        await self.session.flush()
        return embedding


class RelationshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, relationship_id: uuid.UUID) -> Relationship | None:
        result = await self.session.execute(
            select(Relationship).where(Relationship.id == relationship_id)
        )
        return result.scalars().first()

    async def list_by_licitacion(self, licitacion_id: int) -> list[Relationship]:
        result = await self.session.execute(
            select(Relationship)
            .where(Relationship.licitacion_id == licitacion_id)
            .order_by(desc(Relationship.confidence_score))
        )
        return list(result.scalars().all())

    async def create_many(self, relationships: Sequence[Relationship]) -> list[Relationship]:
        for rel in relationships:
            self.session.add(rel)
        await self.session.flush()
        return list(relationships)


class TaxonomyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_category_by_id(self, category_id: int) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalars().first()

    async def get_category_by_code(self, code: str) -> Category | None:
        result = await self.session.execute(
            select(Category).where(Category.code == code)
        )
        return result.scalars().first()

    async def list_categories(self, taxonomy_version: str | None = None) -> list[Category]:
        stmt = select(Category)
        if taxonomy_version is not None:
            stmt = stmt.where(Category.taxonomy_version == taxonomy_version)
        stmt = stmt.order_by(Category.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_subcategory_by_id(self, subcategory_id: int) -> Subcategory | None:
        result = await self.session.execute(
            select(Subcategory).where(Subcategory.id == subcategory_id)
        )
        return result.scalars().first()

    async def get_subcategory_by_code(
        self, category_id: int, code: str
    ) -> Subcategory | None:
        result = await self.session.execute(
            select(Subcategory).where(
                Subcategory.category_id == category_id,
                Subcategory.code == code,
            )
        )
        return result.scalars().first()

    async def list_subcategories(
        self, category_id: int | None = None, taxonomy_version: str | None = None
    ) -> list[Subcategory]:
        stmt = select(Subcategory)
        if category_id is not None:
            stmt = stmt.where(Subcategory.category_id == category_id)
        if taxonomy_version is not None:
            stmt = stmt.where(Subcategory.taxonomy_version == taxonomy_version)
        stmt = stmt.order_by(Subcategory.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_full_tree(self, taxonomy_version: str | None = None) -> list[dict]:
        cats = await self.list_categories(taxonomy_version=taxonomy_version)
        tree = []
        for cat in cats:
            subs = await self.list_subcategories(category_id=cat.id, taxonomy_version=taxonomy_version)
            sub_list = []
            for sub in subs:
                conc_result = await self.session.execute(
                    select(Concept).where(Concept.subcategory_id == sub.id).order_by(Concept.code)
                )
                concepts = list(conc_result.scalars().all())
                sub_list.append({
                    "id": sub.id,
                    "code": sub.code,
                    "name": sub.name,
                    "description": sub.description,
                    "concepts": [{"id": c.id, "code": c.code, "name": c.name} for c in concepts],
                })
            tree.append({
                "id": cat.id,
                "code": cat.code,
                "name": cat.name,
                "description": cat.description,
                "subcategories": sub_list,
            })
        return tree


class DictionaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_keyword(
        self, term: str, dictionary_version: str | None = None
    ) -> Keyword | None:
        stmt = select(Keyword).where(Keyword.term == term)
        if dictionary_version is not None:
            stmt = stmt.where(Keyword.dictionary_version == dictionary_version)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_keywords(
        self, dictionary_version: str | None = None
    ) -> list[Keyword]:
        stmt = select(Keyword)
        if dictionary_version is not None:
            stmt = stmt.where(Keyword.dictionary_version == dictionary_version)
        stmt = stmt.order_by(Keyword.term)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_product_concept_by_code(
        self, code: str, dictionary_version: str | None = None
    ) -> ProductConcept | None:
        stmt = select(ProductConcept).where(ProductConcept.code == code)
        if dictionary_version is not None:
            stmt = stmt.where(ProductConcept.dictionary_version == dictionary_version)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_product_concepts(
        self, dictionary_version: str | None = None
    ) -> list[ProductConcept]:
        stmt = select(ProductConcept)
        if dictionary_version is not None:
            stmt = stmt.where(ProductConcept.dictionary_version == dictionary_version)
        stmt = stmt.order_by(ProductConcept.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_keyword(self, keyword: Keyword) -> Keyword:
        self.session.add(keyword)
        await self.session.flush()
        return keyword

    async def create_product_concept(self, concept: ProductConcept) -> ProductConcept:
        self.session.add(concept)
        await self.session.flush()
        return concept


class ModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, model_id: uuid.UUID) -> ModelVersion | None:
        result = await self.session.execute(
            select(ModelVersion).where(ModelVersion.id == model_id)
        )
        return result.scalars().first()

    async def get_by_version(self, name: str, version: str) -> ModelVersion | None:
        result = await self.session.execute(
            select(ModelVersion).where(
                ModelVersion.name == name,
                ModelVersion.version == version,
            )
        )
        return result.scalars().first()

    async def get_active_model(
        self, kind: str = "classifier", preferred_status: str = "production"
    ) -> ModelVersion | None:
        result = await self.session.execute(
            select(ModelVersion)
            .where(ModelVersion.kind == kind, ModelVersion.status == preferred_status)
            .order_by(desc(ModelVersion.created_at))
            .limit(1)
        )
        model = result.scalars().first()
        if model is None and preferred_status == "production":
            # Fallback to staging
            result = await self.session.execute(
                select(ModelVersion)
                .where(ModelVersion.kind == kind, ModelVersion.status == "staging")
                .order_by(desc(ModelVersion.created_at))
                .limit(1)
            )
            model = result.scalars().first()
        return model

    async def list_versions(
        self, kind: str | None = None, status: str | None = None
    ) -> list[ModelVersion]:
        stmt = select(ModelVersion)
        if kind is not None:
            stmt = stmt.where(ModelVersion.kind == kind)
        if status is not None:
            stmt = stmt.where(ModelVersion.status == status)
        stmt = stmt.order_by(desc(ModelVersion.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_models(
        self, kind: str | None = None, status: str | None = None
    ) -> list[ModelVersion]:
        return await self.list_versions(kind=kind, status=status)

    async def list_dataset_versions(self) -> list[DatasetVersion]:
        stmt = select(DatasetVersion).order_by(desc(DatasetVersion.created_at))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_dataset_version(self, dataset_id: uuid.UUID) -> DatasetVersion | None:
        result = await self.session.execute(
            select(DatasetVersion).where(DatasetVersion.id == dataset_id)
        )
        return result.scalars().first()

    async def create(self, model_version: ModelVersion) -> ModelVersion:
        self.session.add(model_version)
        await self.session.flush()
        return model_version

    async def update_status(self, model_id: uuid.UUID, status: str) -> ModelVersion | None:
        await self.session.execute(
            update(ModelVersion)
            .where(ModelVersion.id == model_id)
            .values(status=status)
        )
        await self.session.flush()
        return await self.get(model_id)

    async def promote(
        self, model_id: uuid.UUID, target_status: str
    ) -> tuple[ModelVersion, ModelVersion | None]:
        model = await self.get(model_id)
        if model is None:
            raise ValueError(f"ModelVersion '{model_id}' no encontrado")

        current_state = ModelLifecycleState(model.status)
        target_state = ModelLifecycleState(target_status)
        validate_model_transition(current_state, target_state)

        demoted_model: ModelVersion | None = None
        if target_state == ModelLifecycleState.PRODUCTION:
            current_prod_res = await self.session.execute(
                select(ModelVersion).where(
                    ModelVersion.kind == model.kind,
                    ModelVersion.status == ModelLifecycleState.PRODUCTION.value,
                    ModelVersion.id != model.id,
                )
            )
            demoted_model = current_prod_res.scalars().first()
            if demoted_model is not None:
                demoted_model.status = ModelLifecycleState.STAGING.value

        model.status = target_state.value
        await self.session.flush()
        return model, demoted_model

    async def rollback(self, kind: str = "classifier") -> tuple[ModelVersion, ModelVersion]:
        prod_res = await self.session.execute(
            select(ModelVersion)
            .where(ModelVersion.kind == kind, ModelVersion.status == ModelLifecycleState.PRODUCTION.value)
            .order_by(desc(ModelVersion.updated_at))
            .limit(1)
        )
        current_prod = prod_res.scalars().first()
        if current_prod is None:
            raise ValueError(f"No hay un modelo de tipo '{kind}' activo en producción para rollback")

        staging_res = await self.session.execute(
            select(ModelVersion)
            .where(ModelVersion.kind == kind, ModelVersion.status == ModelLifecycleState.STAGING.value)
            .order_by(desc(ModelVersion.created_at))
            .limit(1)
        )
        candidate = staging_res.scalars().first()
        if candidate is None:
            raise ValueError(f"No hay modelos en 'staging' de tipo '{kind}' disponibles para restaurar")

        current_prod.status = ModelLifecycleState.STAGING.value
        candidate.status = ModelLifecycleState.PRODUCTION.value
        await self.session.flush()
        return candidate, current_prod

    async def get_model_lineage(self, model_id: uuid.UUID) -> dict[str, Any] | None:
        model = await self.get(model_id)
        if model is None:
            return None

        params = model.parameters or {}
        dataset_version_id_raw = params.get("dataset_version_id")
        dataset: DatasetVersion | None = None
        if dataset_version_id_raw:
            try:
                ds_uuid = uuid.UUID(str(dataset_version_id_raw))
                dataset = await self.get_dataset_version(ds_uuid)
            except (ValueError, TypeError):
                pass

        pred_count_res = await self.session.execute(
            select(func.count(Classification.id)).where(Classification.model_version_id == model.id)
        )
        predictions_count = pred_count_res.scalar() or 0

        return {
            "model_id": str(model.id),
            "name": model.name,
            "version": model.version,
            "kind": model.kind,
            "status": model.status,
            "artifact_uri": model.artifact_uri,
            "dataset_version_id": str(dataset.id) if dataset else dataset_version_id_raw,
            "dataset_name": dataset.name if dataset else None,
            "dataset_version": dataset.version if dataset else None,
            "dataset_record_count": dataset.record_count if dataset else None,
            "hyperparameters": params.get("hyperparameters") or {},
            "metrics": model.metrics or {},
            "trained_at": params.get("trained_at") or (model.created_at.isoformat() if model.created_at else None),
            "predictions_count": predictions_count,
        }


class HumanReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, review_id: uuid.UUID) -> HumanReview | None:
        result = await self.session.execute(
            select(HumanReview).where(HumanReview.id == review_id)
        )
        return result.scalars().first()

    async def get_by_classification(self, classification_id: uuid.UUID) -> HumanReview | None:
        result = await self.session.execute(
            select(HumanReview).where(HumanReview.classification_id == classification_id)
        )
        return result.scalars().first()

    async def list(
        self, skip: int = 0, limit: int = 100, accepted: bool | None = None
    ) -> list[HumanReview]:
        stmt = select(HumanReview)
        if accepted is not None:
            stmt = stmt.where(HumanReview.accepted == accepted)
        stmt = stmt.order_by(desc(HumanReview.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_or_update(
        self,
        classification_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        accepted: bool,
        relevant: bool,
        category_id: int | None = None,
        subcategory_id: int | None = None,
        relevance_tier: str | None = None,
        reason: str | None = None,
    ) -> HumanReview:
        existing = await self.session.execute(
            select(HumanReview).where(
                HumanReview.classification_id == classification_id,
                HumanReview.reviewer_id == reviewer_id,
            )
        )
        review = existing.scalars().first()
        if review is not None:
            review.accepted = accepted
            review.relevant = relevant
            review.category_id = category_id
            review.subcategory_id = subcategory_id
            review.relevance_tier = relevance_tier
            review.reason = reason
        else:
            review = HumanReview(
                classification_id=classification_id,
                reviewer_id=reviewer_id,
                accepted=accepted,
                relevant=relevant,
                category_id=category_id,
                subcategory_id=subcategory_id,
                relevance_tier=relevance_tier,
                reason=reason,
            )
            self.session.add(review)
        await self.session.flush()
        return review


class NLPJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_id: uuid.UUID) -> NLPJob | None:
        result = await self.session.execute(select(NLPJob).where(NLPJob.id == job_id))
        return result.scalars().first()

    async def get_by_celery_task_id(self, task_id: str) -> NLPJob | None:
        result = await self.session.execute(select(NLPJob).where(NLPJob.celery_task_id == task_id))
        return result.scalars().first()

    async def get_by_idempotency_key(self, idempotency_key: str) -> NLPJob | None:
        result = await self.session.execute(
            select(NLPJob).where(NLPJob.idempotency_key == idempotency_key)
        )
        return result.scalars().first()

    async def list_by_licitacion_id(self, licitacion_id: int) -> list[NLPJob]:
        result = await self.session.execute(
            select(NLPJob)
            .where(NLPJob.licitacion_id == licitacion_id)
            .order_by(desc(NLPJob.created_at))
        )
        return list(result.scalars().all())

    async def create(self, job: NLPJob) -> NLPJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        *,
        duration_seconds: float | None = None,
        completed_stages: list[str] | None = None,
        pending_stages: list[str] | None = None,
        error: dict | None = None,
        result_summary: dict | None = None,
    ) -> NLPJob | None:
        job = await self.get_by_id(job_id)
        if job is None:
            return None
        job.status = status
        if duration_seconds is not None:
            job.duration_seconds = duration_seconds
        if completed_stages is not None:
            job.completed_stages = completed_stages
        if pending_stages is not None:
            job.pending_stages = pending_stages
        if error is not None:
            job.error = error
        if result_summary is not None:
            job.result_summary = result_summary
        await self.session.flush()
        return job

