"""HTTP mapping for stable Identity errors."""

from http import HTTPStatus

from fastapi import Request
from starlette.responses import Response

from app.api.problem import ProblemDetail, problem_response
from app.core.http.context import request_context_from_scope
from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode


async def identity_domain_error_handler(request: Request, error: Exception) -> Response:
    if not isinstance(error, IdentityDomainError):
        raise TypeError("Identity error handler received an unexpected error.")
    context = request_context_from_scope(request.scope)
    return problem_response(
        ProblemDetail(
            type=f"https://spacewhy.local/problems/identity/{error.code.value.lower()}",
            title="Identity request failed",
            status=_status_for(error.code),
            detail=error.detail,
            instance=request.url.path,
            code=error.code.value,
            request_id=context.request_id if context is not None else "unavailable",
        )
    )


def _status_for(code: IdentityErrorCode) -> int:
    if code in {
        IdentityErrorCode.SESSION_INVALID,
        IdentityErrorCode.INVALID_TELEGRAM_INIT_DATA,
        IdentityErrorCode.HANDOFF_INVALID_OR_EXPIRED,
    }:
        return HTTPStatus.UNAUTHORIZED
    if code is IdentityErrorCode.ENROLLMENT_REQUIRED:
        return HTTPStatus.FORBIDDEN
    if code is IdentityErrorCode.RATE_LIMITED:
        return HTTPStatus.TOO_MANY_REQUESTS
    if code in {
        IdentityErrorCode.PHONE_ALREADY_BOUND,
        IdentityErrorCode.CHALLENGE_ATTEMPTS_EXHAUSTED,
    }:
        return HTTPStatus.CONFLICT
    return HTTPStatus.BAD_REQUEST
