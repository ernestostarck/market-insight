from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    adjudicaciones,
    admin,
    ai,
    analytics,
    auth,
    categorias,
    chat,
    compradores,
    contratos,
    documents,
    etl,
    health,
    licitaciones,
    monitoring,
    nlp,
    ordenes_de_compra,
    organismos,
    proveedores,
    search,
    system,
)
from app.core.openapi import AUTH_ERROR_RESPONSES, COMMON_ERROR_RESPONSES
from app.db.dependencies import get_current_user

api_router = APIRouter()

_authenticated = [Depends(get_current_user)]
# Documented on every router whose routes all require a bearer token, so
# Swagger/Redoc list 401/422/429/500 once per router instead of per-route.
_protected_responses = {**AUTH_ERROR_RESPONSES, **COMMON_ERROR_RESPONSES}


api_router.include_router(health.router, tags=["health", "metadata"])
api_router.include_router(system.router, prefix="/system", tags=["System", "Observability"])
# Authenticated by a shared token (not a user JWT): Alertmanager is the only caller.
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Observability"])
api_router.include_router(
    auth.router, prefix="/auth", tags=["Auth"], responses=COMMON_ERROR_RESPONSES
)
api_router.include_router(
    licitaciones.router,
    prefix="/licitaciones",
    tags=["Licitaciones"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    proveedores.router,
    prefix="/proveedores",
    tags=["Proveedores"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    categorias.router,
    prefix="/categorias",
    tags=["Categorias"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    organismos.router,
    prefix="/organismos",
    tags=["Organismos"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    adjudicaciones.router,
    prefix="/adjudicaciones",
    tags=["Adjudicaciones"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    etl.router,
    prefix="/etl",
    tags=["ETL"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    nlp.router,
    prefix="/nlp",
    tags=["NLP"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    compradores.router,
    prefix="/compradores",
    tags=["Compradores"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    contratos.router,
    prefix="/contratos",
    tags=["Contratos"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    ordenes_de_compra.router,
    prefix="/ordenes_de_compra",
    tags=["Ordenes de Compra"],
    dependencies=_authenticated,
    responses=_protected_responses,
)
api_router.include_router(
    ordenes_de_compra.router,
    prefix="/ordenes-de-compra",
    tags=["Ordenes de Compra"],
    dependencies=_authenticated,
    responses=_protected_responses,
    include_in_schema=False,
)
api_router.include_router(
    ordenes_de_compra.router,
    prefix="/ordenes-compra",
    tags=["Ordenes de Compra"],
    dependencies=_authenticated,
    responses=_protected_responses,
    include_in_schema=False,
)
