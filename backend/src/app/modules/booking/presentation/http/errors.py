"""HTTP translation for stable booking domain failures."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import Request
from starlette.responses import Response

from app.api.problem import ProblemDetail, problem_response
from app.core.http.context import request_context_from_scope
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode

_NOT_FOUND_CODES = {
    BookingErrorCode.HOLD_NOT_FOUND,
    BookingErrorCode.APPOINTMENT_NOT_FOUND,
    BookingErrorCode.RESOURCE_NOT_FOUND,
}
_CONFLICT_CODES = {
    BookingErrorCode.SLOT_TAKEN,
    BookingErrorCode.HOLD_EXPIRED,
    BookingErrorCode.HOLD_OWNER_MISMATCH,
    BookingErrorCode.CUSTOMER_BOOKING_LIMIT_REACHED,
    BookingErrorCode.CUSTOMER_TIME_CONFLICT,
    BookingErrorCode.INVALID_APPOINTMENT_STATUS_TRANSITION,
    BookingErrorCode.CANCELLATION_WINDOW_CLOSED,
    BookingErrorCode.RESCHEDULE_NOT_ALLOWED,
    BookingErrorCode.CASH_SHIFT_ALREADY_OPEN,
    BookingErrorCode.PAYMENT_EXCEEDS_OUTSTANDING_AMOUNT,
    BookingErrorCode.REFUND_EXCEEDS_REFUNDABLE_AMOUNT,
    BookingErrorCode.IDEMPOTENCY_CONFLICT,
}
_FORBIDDEN_CODES = {
    BookingErrorCode.FORBIDDEN,
    BookingErrorCode.STAFF_NOT_BOUND,
    BookingErrorCode.CUSTOMER_BLOCKED,
}


async def booking_domain_error_handler(request: Request, error: Exception) -> Response:
    """Render booking failures through the platform Problem Details contract."""

    if not isinstance(error, BookingDomainError):
        raise TypeError("Booking error handler received an unexpected error.")
    context = request_context_from_scope(request.scope)
    status = _status_for(error.code)
    return problem_response(
        ProblemDetail(
            type=f"https://spacewhy.local/problems/booking/{error.code.value.lower()}",
            title="Booking request failed",
            status=status,
            detail=error.detail,
            instance=request.url.path,
            code=error.code.value,
            request_id=context.request_id if context is not None else "unavailable",
        )
    )


def _status_for(code: BookingErrorCode) -> int:
    """Map stable codes to HTTP semantics while clients continue to branch on code."""

    if code is BookingErrorCode.INVALID_TELEGRAM_INIT_DATA:
        return HTTPStatus.UNAUTHORIZED
    if code is BookingErrorCode.RATE_LIMITED:
        return HTTPStatus.TOO_MANY_REQUESTS
    if code in _NOT_FOUND_CODES:
        return HTTPStatus.NOT_FOUND
    if code in _CONFLICT_CODES:
        return HTTPStatus.CONFLICT
    if code in _FORBIDDEN_CODES:
        return HTTPStatus.FORBIDDEN
    return HTTPStatus.BAD_REQUEST
