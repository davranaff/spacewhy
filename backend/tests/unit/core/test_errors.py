"""Framework-independent error hierarchy tests."""

from app.core.errors.codes import ErrorCode
from app.core.errors.exceptions import (
    ApplicationError,
    ConflictError,
    DependencyUnavailableError,
    NotFoundError,
    ValidationError,
)


def test_error_codes_are_stable_and_framework_independent() -> None:
    """Expected errors retain their machine codes without HTTP inheritance."""

    assert ValidationError().code is ErrorCode.INVALID_REQUEST
    assert NotFoundError().code is ErrorCode.RESOURCE_NOT_FOUND
    assert ConflictError().code is ErrorCode.CONFLICT
    assert DependencyUnavailableError().code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert not hasattr(ApplicationError, "status_code")


def test_application_error_uses_safe_default_detail() -> None:
    """A typed error always provides a presentation-safe default detail."""

    assert NotFoundError().detail == "The requested resource does not exist."
