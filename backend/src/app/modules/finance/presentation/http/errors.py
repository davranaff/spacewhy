"""HTTP mapping for Finance domain outcomes."""

from http import HTTPStatus

from fastapi import Request
from starlette.responses import Response

from app.api.problem import ProblemDetail, problem_response
from app.core.http.context import request_context_from_scope
from app.modules.finance.domain.errors import FinanceDomainError, FinanceErrorCode

_NOT_FOUND = {
    FinanceErrorCode.ACCOUNT_NOT_FOUND,
    FinanceErrorCode.CATEGORY_NOT_FOUND,
}
_CONFLICT = {
    FinanceErrorCode.ACCOUNT_ARCHIVED,
    FinanceErrorCode.CATEGORY_DIRECTION_MISMATCH,
    FinanceErrorCode.CURRENCY_MISMATCH,
    FinanceErrorCode.IDEMPOTENCY_CONFLICT,
}


async def finance_domain_error_handler(request: Request, error: Exception) -> Response:
    if not isinstance(error, FinanceDomainError):
        raise TypeError("Finance error handler received an unexpected error.")
    context = request_context_from_scope(request.scope)
    return problem_response(
        ProblemDetail(
            type=f"https://spacewhy.local/problems/finance/{error.code.value.lower()}",
            title="Finance request failed",
            status=_status_for(error.code),
            detail=error.detail,
            instance=request.url.path,
            code=error.code.value,
            request_id=context.request_id if context is not None else "unavailable",
        )
    )


def _status_for(code: FinanceErrorCode) -> int:
    if code in _NOT_FOUND:
        return HTTPStatus.NOT_FOUND
    if code in _CONFLICT:
        return HTTPStatus.CONFLICT
    if code in {FinanceErrorCode.MEMBERSHIP_REQUIRED, FinanceErrorCode.PERMISSION_DENIED}:
        return HTTPStatus.FORBIDDEN
    return HTTPStatus.BAD_REQUEST
