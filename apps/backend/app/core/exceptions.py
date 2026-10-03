import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.integrations.chilecompra.exceptions import (
    ChileCompraAPIError,
    ChileCompraAuthenticationError,
    ChileCompraError,
    ChileCompraNotFoundError,
    ChileCompraRateLimitError,
    ChileCompraTimeoutError,
    ChileCompraValidationError,
)
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self, message: str, *, code: str = "BAD_REQUEST", status_code: int = 400
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        level,
        "%s: %s",
        exc.code,
        exc.message,
        extra={"http_status_code": exc.status_code, "error_code": exc.code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                request_id=getattr(request.state, "request_id", None),
            )
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    logger.warning(
        "VALIDATION_ERROR: %s", exc.errors(), extra={"http_status_code": 422}
    )
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message=str(exc.errors()),
                request_id=getattr(request.state, "request_id", None),
            )
        ).model_dump(),
    )


def _chilecompra_error_mapping(exc: ChileCompraError) -> tuple[int, str]:
    if isinstance(exc, ChileCompraValidationError):
        return 422, "CHILECOMPRA_VALIDATION_ERROR"
    if isinstance(exc, ChileCompraAuthenticationError):
        return 502, "CHILECOMPRA_AUTH_ERROR"
    if isinstance(exc, ChileCompraNotFoundError):
        return 502, "CHILECOMPRA_NOT_FOUND"
    if isinstance(exc, ChileCompraRateLimitError):
        return 429, "CHILECOMPRA_RATE_LIMIT"
    if isinstance(exc, ChileCompraTimeoutError):
        return 504, "CHILECOMPRA_TIMEOUT"
    if isinstance(exc, ChileCompraAPIError):
        return 502, "CHILECOMPRA_API_ERROR"
    return 502, "CHILECOMPRA_UNHANDLED_ERROR"


async def chilecompra_exception_handler(
    request: Request, exc: ChileCompraError
) -> JSONResponse:
    status_code, error_code = _chilecompra_error_mapping(exc)
    level = logging.ERROR if status_code >= 500 else logging.WARNING
    logger.log(
        level,
        "%s: %s",
        error_code,
        exc,
        extra={"http_status_code": status_code, "error_code": error_code},
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=error_code,
                message=str(exc),
                request_id=getattr(request.state, "request_id", None),
            )
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
                request_id=getattr(request.state, "request_id", None),
            )
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ChileCompraError, chilecompra_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
