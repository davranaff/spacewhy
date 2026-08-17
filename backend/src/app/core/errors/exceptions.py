"""Errors that model application outcomes without HTTP framework coupling."""

from __future__ import annotations

from typing import ClassVar

from app.core.errors.codes import ErrorCode


class ApplicationError(Exception):
    """Base class for expected, safely reportable application failures."""

    code: ClassVar[ErrorCode] = ErrorCode.INTERNAL_SERVER_ERROR
    title: ClassVar[str] = "Application error"
    default_detail: ClassVar[str] = "The request could not be completed."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class ValidationError(ApplicationError):
    """The requested operation violates an application validation rule."""

    code = ErrorCode.INVALID_REQUEST
    title = "Invalid request"
    default_detail = "The request could not be processed."


class NotFoundError(ApplicationError):
    """The requested resource does not exist in the current scope."""

    code = ErrorCode.RESOURCE_NOT_FOUND
    title = "Resource not found"
    default_detail = "The requested resource does not exist."


class ConflictError(ApplicationError):
    """The requested state transition conflicts with current state."""

    code = ErrorCode.CONFLICT
    title = "Conflict"
    default_detail = "The request conflicts with the current resource state."


class AuthenticationError(ApplicationError):
    """The caller must authenticate before performing the operation."""

    code = ErrorCode.AUTHENTICATION_REQUIRED
    title = "Authentication required"
    default_detail = "Authentication is required for this operation."


class AuthorizationError(ApplicationError):
    """The authenticated caller is not allowed to perform the operation."""

    code = ErrorCode.AUTHORIZATION_DENIED
    title = "Authorization denied"
    default_detail = "You are not allowed to perform this operation."


class RateLimitError(ApplicationError):
    """A future rate-limiting adapter may raise this stable outcome."""

    code = ErrorCode.RATE_LIMITED
    title = "Too many requests"
    default_detail = "Too many requests were received. Please try again later."


class DependencyUnavailableError(ApplicationError):
    """A required infrastructure dependency is temporarily unavailable."""

    code = ErrorCode.DEPENDENCY_UNAVAILABLE
    title = "Dependency unavailable"
    default_detail = "A required service is temporarily unavailable."
