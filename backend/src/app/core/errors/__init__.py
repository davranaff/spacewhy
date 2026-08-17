"""Framework-independent application errors and stable codes."""

from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "ApplicationError",
    "AuthenticationError",
    "AuthorizationError",
    "ConflictError",
    "DependencyUnavailableError",
    "ErrorCode",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
]
