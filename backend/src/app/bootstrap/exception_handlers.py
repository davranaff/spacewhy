"""Single HTTP mapping point for framework-independent application errors."""

from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.problem import ProblemDetail, problem_response
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
from app.core.http.context import request_context_from_scope, route_template_from_scope
from app.modules.booking.domain.errors import BookingDomainError
from app.modules.booking.presentation.http.errors import booking_domain_error_handler
from app.modules.finance.domain.errors import FinanceDomainError
from app.modules.finance.presentation.http.errors import finance_domain_error_handler
from app.modules.identity.domain.errors import IdentityDomainError
from app.modules.identity.presentation.http.errors import identity_domain_error_handler

logger = logging.getLogger("spacewhy")

_APPLICATION_ERROR_STATUSES: tuple[tuple[type[ApplicationError], int], ...] = (
    (ValidationError, HTTPStatus.BAD_REQUEST),
    (NotFoundError, HTTPStatus.NOT_FOUND),
    (ConflictError, HTTPStatus.CONFLICT),
    (AuthenticationError, HTTPStatus.UNAUTHORIZED),
    (AuthorizationError, HTTPStatus.FORBIDDEN),
    (RateLimitError, HTTPStatus.TOO_MANY_REQUESTS),
    (DependencyUnavailableError, HTTPStatus.SERVICE_UNAVAILABLE),
)


def _request_id(request: Request) -> str:
    """Return middleware context or an explicit fallback for malformed ASGI calls."""

    context = request_context_from_scope(request.scope)
    return context.request_id if context is not None else "unavailable"


def _problem(
    request: Request,
    *,
    problem_type: str,
    title: str,
    status_code: int,
    detail: str,
    code: ErrorCode,
) -> ProblemDetail:
    """Build a safe Problem Details document without query-string leakage."""

    return ProblemDetail(
        type=f"https://spacewhy.local/problems/{problem_type}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=_request_id(request),
    )


def _status_for_application_error(error: ApplicationError) -> int:
    """Map error classes at the HTTP boundary without HTTP coupling in core."""

    for error_type, status_code in _APPLICATION_ERROR_STATUSES:
        if isinstance(error, error_type):
            return status_code
    return HTTPStatus.INTERNAL_SERVER_ERROR


async def application_error_handler(request: Request, error: Exception) -> Response:
    """Render expected application failures as safe Problem Details."""

    if not isinstance(error, ApplicationError):
        raise TypeError("Application error handler received an unexpected exception.")
    return problem_response(
        _problem(
            request,
            problem_type=error.code.lower().replace("_", "-"),
            title=error.title,
            status_code=_status_for_application_error(error),
            detail=error.detail,
            code=error.code,
        )
    )


async def request_validation_error_handler(
    request: Request,
    error: Exception,
) -> Response:
    """Avoid exposing framework validation internals while retaining a stable code."""

    if not isinstance(error, RequestValidationError):
        raise TypeError("Validation handler received an unexpected exception.")
    return problem_response(
        _problem(
            request,
            problem_type="request-validation-failed",
            title="Request validation failed",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="One or more request values are invalid.",
            code=ErrorCode.INVALID_REQUEST,
        )
    )


async def http_exception_handler(request: Request, error: Exception) -> Response:
    """Map routing and method errors into the shared Problem Details contract."""

    if not isinstance(error, StarletteHTTPException):
        raise TypeError("HTTP exception handler received an unexpected exception.")
    if error.status_code == HTTPStatus.NOT_FOUND:
        problem_type = "route-not-found"
        title = "Route not found"
        detail = "The requested route does not exist."
        code = ErrorCode.ROUTE_NOT_FOUND
    elif error.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
        problem_type = "method-not-allowed"
        title = "Method not allowed"
        detail = "The request method is not allowed for this route."
        code = ErrorCode.METHOD_NOT_ALLOWED
    else:
        problem_type = "http-error"
        title = HTTPStatus(error.status_code).phrase
        detail = "The request could not be completed."
        code = ErrorCode.INVALID_REQUEST
    return problem_response(
        _problem(
            request,
            problem_type=problem_type,
            title=title,
            status_code=error.status_code,
            detail=detail,
            code=code,
        )
    )


async def unexpected_exception_handler(request: Request, error: Exception) -> Response:
    """Log the stack trace internally and return no implementation details to clients."""

    logger.error(
        "unhandled_exception",
        exc_info=(type(error), error, error.__traceback__),
        extra={
            "request_id": _request_id(request),
            "route": route_template_from_scope(request.scope),
            "status_code": HTTPStatus.INTERNAL_SERVER_ERROR,
        },
    )
    return problem_response(
        _problem(
            request,
            problem_type="internal-server-error",
            title="Internal server error",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
            code=ErrorCode.INTERNAL_SERVER_ERROR,
        )
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register every framework and application error handler exactly once per app."""

    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(BookingDomainError, booking_domain_error_handler)
    app.add_exception_handler(IdentityDomainError, identity_domain_error_handler)
    app.add_exception_handler(FinanceDomainError, finance_domain_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
