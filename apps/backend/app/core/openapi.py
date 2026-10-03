from __future__ import annotations

from typing import Any

from app.schemas.errors import ErrorResponse

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": "Liveness/readiness checks used by orchestrators and uptime monitors. Public, unauthenticated.",
    },
    {
        "name": "metadata",
        "description": "Service metadata (name, version, environment).",
    },
    {
        "name": "Auth",
        "description": "Registration and JWT-based login. `POST /auth/login` issues the bearer token every other "
        "endpoint requires via `Authorization: Bearer <token>`.",
    },
    {
        "name": "Licitaciones",
        "description": "Public tenders (licitaciones) published through ChileCompra.",
    },
    {
        "name": "Proveedores",
        "description": "Suppliers (proveedores) that participate in public procurement.",
    },
    {
        "name": "Organismos",
        "description": "Public buying agencies (organismos compradores).",
    },
    {
        "name": "Compradores",
        "description": "Individual buyers/purchasing officers associated with organismos.",
    },
    {
        "name": "Contratos",
        "description": "Awarded contracts (contratos) tied to tenders and suppliers.",
    },
    {
        "name": "Ordenes de Compra",
        "description": "Purchase orders (ordenes de compra) issued under framework agreements.",
    },
    {
        "name": "Documents",
        "description": "Upload, download and signed-URL retrieval for tender-related documents, backed by object storage.",
    },
    {
        "name": "Search",
        "description": "Federated full-text search across licitaciones, proveedores and organismos in a single call.",
    },
    {
        "name": "Analytics",
        "description": "Read-only market indicators, supplier performance, spending breakdowns and adjudicacion "
        "opportunity/risk scoring built on top of the analytical data marts.",
    },
    {
        "name": "ETL",
        "description": "Trigger and monitor asynchronous ETL jobs that ingest data from ChileCompra into the "
        "canonical model. Job status is polled via Celery task IDs.",
    },
    {
        "name": "NLP",
        "description": "Text normalization and deterministic tender classification foundations.",
    },
    {
        "name": "NLP",
        "description": "Text normalization and deterministic tender classification foundations.",
    },
]

# Applied via `include_router(..., responses=...)` so Swagger/Redoc document the
# error envelope shape once instead of repeating it on every single route.
AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing, malformed or expired bearer token.", "model": ErrorResponse},
}

COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"description": "Request failed validation.", "model": ErrorResponse},
    429: {
        "description": "Rate limit exceeded. Retry after the seconds given in the `Retry-After` header.",
        "model": ErrorResponse,
    },
    500: {"description": "Unexpected internal server error.", "model": ErrorResponse},
}
