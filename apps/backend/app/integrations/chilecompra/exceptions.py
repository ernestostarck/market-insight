class ChileCompraError(Exception):
    """Base error for the internal ChileCompra SDK."""


class ChileCompraTimeoutError(ChileCompraError):
    """Raised when a request to ChileCompra times out."""


class ChileCompraAuthenticationError(ChileCompraError):
    """Raised when ChileCompra rejects the ticket or credentials."""


class ChileCompraRateLimitError(ChileCompraError):
    """Raised when ChileCompra rate limits the client."""


class ChileCompraNotFoundError(ChileCompraError):
    """Raised when ChileCompra returns a 404 response."""


class ChileCompraValidationError(ChileCompraError):
    """Raised when the request is invalid for ChileCompra."""


class ChileCompraAPIError(ChileCompraError):
    """Raised for non-recoverable ChileCompra API errors."""
