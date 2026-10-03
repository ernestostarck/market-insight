"""Unit tests verifying all dependency injection providers in app.db.dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db import dependencies as deps
from app.repositories.comprador import CompradorRepository
from app.repositories.contrato import ContratoRepository
from app.repositories.knowledge import (
    ClassificationRepository,
    EntityRepository,
    ModelRepository,
    NLPJobRepository,
    RelationshipRepository,
)
from app.repositories.licitacion import LicitacionRepository
from app.repositories.orden_de_compra import OrdenDeCompraRepository
from app.repositories.organismo import OrganismoRepository
from app.repositories.proveedor import ProveedorRepository
from app.repositories.user import UserRepository
from app.services.comprador import CompradorService
from app.services.contrato import ContratoService
from app.services.licitacion import LicitacionService
from app.services.nlp import (
    ClassificationService,
    EmbeddingService,
    EntityExtractionService,
    ModelManagementService,
    NLPService,
    ProductExtractionService,
    RelevanceService,
    ReviewService,
    RuleClassificationService,
    SemanticSearchService,
    TaxonomyService,
)
from app.services.orden_de_compra import OrdenDeCompraService
from app.services.organismo import OrganismoService
from app.services.proveedor import ProveedorService
from app.services.search import SearchService


def test_core_and_domain_dependencies() -> None:
    mock_session = AsyncMock()

    # User
    user_repo = deps.get_user_repository(mock_session)
    assert isinstance(user_repo, UserRepository)

    # Licitacion
    lic_repo = deps.get_licitacion_repository(mock_session)
    lic_svc = deps.get_licitacion_service(lic_repo)
    assert isinstance(lic_repo, LicitacionRepository)
    assert isinstance(lic_svc, LicitacionService)

    # Proveedor
    prov_repo = deps.get_proveedor_repository(mock_session)
    prov_svc = deps.get_proveedor_service(prov_repo)
    assert isinstance(prov_repo, ProveedorRepository)
    assert isinstance(prov_svc, ProveedorService)

    # Organismo
    org_repo = deps.get_organismo_repository(mock_session)
    org_svc = deps.get_organismo_service(org_repo)
    assert isinstance(org_repo, OrganismoRepository)
    assert isinstance(org_svc, OrganismoService)

    # Comprador
    comp_repo = deps.get_comprador_repository(mock_session)
    comp_svc = deps.get_comprador_service(comp_repo)
    assert isinstance(comp_repo, CompradorRepository)
    assert isinstance(comp_svc, CompradorService)

    # Contrato
    cont_repo = deps.get_contrato_repository(mock_session)
    cont_svc = deps.get_contrato_service(cont_repo)
    assert isinstance(cont_repo, ContratoRepository)
    assert isinstance(cont_svc, ContratoService)

    # Orden de Compra (Regression test for import bug)
    oc_repo = deps.get_orden_de_compra_repository(mock_session)
    oc_svc = deps.get_orden_de_compra_service(oc_repo)
    assert isinstance(oc_repo, OrdenDeCompraRepository)
    assert isinstance(oc_svc, OrdenDeCompraService)

    # Search & Analytics & NLP base
    search_svc = deps.get_search_service(lic_repo, prov_repo, org_repo)
    assert isinstance(search_svc, SearchService)

    analytics_repo = deps.get_analytics_repository(mock_session)
    assert analytics_repo is not None

    nlp_svc = deps.get_nlp_service()
    assert isinstance(nlp_svc, NLPService)


def test_ai_and_nlp_dependencies() -> None:
    mock_session = AsyncMock()

    # Repositories
    cls_repo = deps.get_classification_repository(mock_session)
    assert isinstance(cls_repo, ClassificationRepository)

    model_repo = deps.get_model_repository(mock_session)
    assert isinstance(model_repo, ModelRepository)

    job_repo = deps.get_nlp_job_repository(mock_session)
    assert isinstance(job_repo, NLPJobRepository)

    # NLP Services
    tax_svc = deps.get_taxonomy_service()
    assert isinstance(tax_svc, TaxonomyService)

    rel_svc = deps.get_relevance_service()
    assert isinstance(rel_svc, RelevanceService)

    rule_svc = deps.get_rule_classification_service()
    assert isinstance(rule_svc, RuleClassificationService)

    embed_svc = deps.get_embedding_service()
    assert isinstance(embed_svc, EmbeddingService)

    ent_svc = deps.get_entity_extraction_service(mock_session)
    assert isinstance(ent_svc, EntityExtractionService)

    prod_svc = deps.get_product_extraction_service()
    assert isinstance(prod_svc, ProductExtractionService)

    review_svc = deps.get_review_service(tax_svc)
    assert isinstance(review_svc, ReviewService)

    cls_svc = deps.get_classification_service(
        rule_service=rule_svc,
        embedding_service=embed_svc,
        taxonomy_service=tax_svc,
        relevance_service=rel_svc,
        classification_repository=cls_repo,
    )
    assert isinstance(cls_svc, ClassificationService)

    sem_search_svc = deps.get_semantic_search_service(
        session=mock_session,
        embedding_service=embed_svc,
        taxonomy_service=tax_svc,
    )
    assert isinstance(sem_search_svc, SemanticSearchService)

    model_mgmt_svc = deps.get_model_management_service(model_repo)
    assert isinstance(model_mgmt_svc, ModelManagementService)
