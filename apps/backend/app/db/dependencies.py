"""Application-wide dependency injection providers for FastAPI."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.nlp.apparel_rules import build_apparel_ruleset
from app.nlp.dictionary import load_initial_dictionary
from app.nlp.dispatch import CeleryNLPJobDispatcher
from app.nlp.preprocessing import TextPreprocessor
from app.nlp.rules import RuleEngine, build_ruleset
from app.nlp.segmento import Segmento, licitacion_ids_for, resolve_segmento
from app.nlp.taxonomy import load_initial_taxonomy
from app.repositories.adjudicacion import AdjudicacionRepository
from app.repositories.analytics import AnalyticsRepository
from app.repositories.categoria import CategoriaRepository
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
from app.repositories.vector_search import VectorSearchRepository
from app.services.auth import AuthService
from app.services.categoria import CategoriaService
from app.services.comprador import CompradorService
from app.services.contrato import ContratoService
from app.services.licitacion import LicitacionService
from app.services.nlp import (
    ClassificationService,
    EmbeddingService,
    EntityExtractionService,
    ModelManagementService,
    NLPService,
    PreprocessingService,
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

_settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{_settings.api_v1_prefix}/auth/login")
_RULE_ENGINE = RuleEngine(
    build_ruleset(load_initial_dictionary(), load_initial_taxonomy()) + build_apparel_ruleset()
)


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the authenticated user from the bearer token.

    Besides signature/expiry/issuer/audience, the token must match the user's current
    `token_version` and its session must not be revoked, so logout, "sign out
    everywhere", password changes and admin deactivation take effect immediately.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    resolved = await auth_service.user_from_access_token(token)
    if resolved is None:
        raise credentials_exception
    user, session_id = resolved
    request.state.user_id = user.id
    request.state.session_id = session_id
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador.",
        )
    return current_user


def get_licitacion_repository(
    session: AsyncSession = Depends(get_db),
) -> LicitacionRepository:
    return LicitacionRepository(session)


def get_licitacion_service(
    repository: LicitacionRepository = Depends(get_licitacion_repository),
) -> LicitacionService:
    return LicitacionService(repository)


def get_proveedor_repository(
    session: AsyncSession = Depends(get_db),
) -> ProveedorRepository:
    return ProveedorRepository(session)


def get_proveedor_service(
    repository: ProveedorRepository = Depends(get_proveedor_repository),
) -> ProveedorService:
    return ProveedorService(repository)


def get_categoria_repository(
    session: AsyncSession = Depends(get_db),
) -> CategoriaRepository:
    return CategoriaRepository(session)


def get_categoria_service(
    repository: CategoriaRepository = Depends(get_categoria_repository),
) -> CategoriaService:
    return CategoriaService(repository)


def get_organismo_repository(
    session: AsyncSession = Depends(get_db),
) -> OrganismoRepository:
    return OrganismoRepository(session)


def get_organismo_service(
    repository: OrganismoRepository = Depends(get_organismo_repository),
) -> OrganismoService:
    return OrganismoService(repository)


def get_search_service(
    licitacion_repository: LicitacionRepository = Depends(get_licitacion_repository),
    proveedor_repository: ProveedorRepository = Depends(get_proveedor_repository),
    organismo_repository: OrganismoRepository = Depends(get_organismo_repository),
) -> SearchService:
    """Return the federated search service using the request's DB session."""
    return SearchService(
        licitacion_repository=licitacion_repository,
        proveedor_repository=proveedor_repository,
        organismo_repository=organismo_repository,
    )


def get_nlp_service() -> NLPService:
    """Return the deterministic NLP foundations, with the real initial ruleset (6.7)."""
    return NLPService(
        preprocessor=TextPreprocessor(),
        rule_engine=_RULE_ENGINE,
        dispatcher=CeleryNLPJobDispatcher(),
    )


def get_adjudicacion_repository(
    session: AsyncSession = Depends(get_db),
) -> AdjudicacionRepository:
    return AdjudicacionRepository(session)


def get_analytics_repository(
    session: AsyncSession = Depends(get_db),
) -> AnalyticsRepository:
    """Return the read-only repository for analytics views and snapshots."""
    return AnalyticsRepository(session)


async def get_segmento(
    segmento: str | None = Query(
        None,
        max_length=128,
        description="Market segment picked on the Rubros page: `cat:<category_code>` or "
        "`concept:<concept_code>` from the classification taxonomy.",
    ),
) -> Segmento | None:
    if not segmento:
        return None
    resolved = resolve_segmento(segmento)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown segmento '{segmento}'",
        )
    return resolved


async def get_segmento_licitacion_ids(
    segmento: Segmento | None = Depends(get_segmento),
    session: AsyncSession = Depends(get_db),
) -> list[int] | None:
    """Ids of the licitaciones in the requested segmento, or None when unscoped."""
    if segmento is None:
        return None
    return await licitacion_ids_for(session, segmento)


def get_comprador_repository(
    session: AsyncSession = Depends(get_db),
) -> CompradorRepository:
    return CompradorRepository(session)


def get_comprador_service(
    repository: CompradorRepository = Depends(get_comprador_repository),
) -> CompradorService:
    return CompradorService(repository)


def get_contrato_repository(
    session: AsyncSession = Depends(get_db),
) -> ContratoRepository:
    return ContratoRepository(session)


def get_contrato_service(
    repository: ContratoRepository = Depends(get_contrato_repository),
) -> ContratoService:
    return ContratoService(repository)


def get_orden_de_compra_repository(
    session: AsyncSession = Depends(get_db),
) -> OrdenDeCompraRepository:
    return OrdenDeCompraRepository(session)


def get_orden_de_compra_service(
    repository: OrdenDeCompraRepository = Depends(get_orden_de_compra_repository),
) -> OrdenDeCompraService:
    return OrdenDeCompraService(repository)


def get_classification_repository(
    session: AsyncSession = Depends(get_db),
) -> ClassificationRepository:
    return ClassificationRepository(session)


def get_model_repository(
    session: AsyncSession = Depends(get_db),
) -> ModelRepository:
    return ModelRepository(session)


def get_nlp_job_repository(
    session: AsyncSession = Depends(get_db),
) -> NLPJobRepository:
    return NLPJobRepository(session)


def get_taxonomy_service() -> TaxonomyService:
    return TaxonomyService()


def get_relevance_service() -> RelevanceService:
    return RelevanceService()


def get_rule_classification_service() -> RuleClassificationService:
    return RuleClassificationService()


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def get_entity_extraction_service(
    session: AsyncSession = Depends(get_db),
) -> EntityExtractionService:
    return EntityExtractionService(
        entity_repository=EntityRepository(session),
        relationship_repository=RelationshipRepository(session),
    )


def get_product_extraction_service() -> ProductExtractionService:
    return ProductExtractionService()


def get_review_service(
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> ReviewService:
    return ReviewService(taxonomy_service=taxonomy_service)


def get_classification_service(
    rule_service: RuleClassificationService = Depends(get_rule_classification_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    relevance_service: RelevanceService = Depends(get_relevance_service),
    classification_repository: ClassificationRepository = Depends(get_classification_repository),
) -> ClassificationService:
    return ClassificationService(
        preprocessing_service=PreprocessingService(),
        rule_service=rule_service,
        embedding_service=embedding_service,
        taxonomy_service=taxonomy_service,
        relevance_service=relevance_service,
        classification_repository=classification_repository,
    )


def get_semantic_search_service(
    session: AsyncSession = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
) -> SemanticSearchService:
    return SemanticSearchService(
        vector_repository=VectorSearchRepository(session),
        embedding_service=embedding_service._base,
        taxonomy=taxonomy_service._taxonomy,
    )


def get_model_management_service(
    model_repository: ModelRepository = Depends(get_model_repository),
) -> ModelManagementService:
    return ModelManagementService(model_repository)
