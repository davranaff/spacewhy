"""Framework-independent booking failures with stable frontend error codes."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class BookingErrorCode(StrEnum):
    """Machine-readable booking outcomes."""

    SLOT_TAKEN = "SLOT_TAKEN"
    HOLD_EXPIRED = "HOLD_EXPIRED"
    HOLD_NOT_FOUND = "HOLD_NOT_FOUND"
    HOLD_OWNER_MISMATCH = "HOLD_OWNER_MISMATCH"
    OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
    SERVICE_INACTIVE = "SERVICE_INACTIVE"
    SPECIALIST_INACTIVE = "SPECIALIST_INACTIVE"
    SPECIALIST_DOES_NOT_PROVIDE_SERVICE = "SPECIALIST_DOES_NOT_PROVIDE_SERVICE"
    SPECIALIST_UNAVAILABLE = "SPECIALIST_UNAVAILABLE"
    BRANCH_INACTIVE = "BRANCH_INACTIVE"
    BOOKING_TOO_EARLY = "BOOKING_TOO_EARLY"
    BOOKING_TOO_FAR_IN_FUTURE = "BOOKING_TOO_FAR_IN_FUTURE"
    CUSTOMER_BOOKING_LIMIT_REACHED = "CUSTOMER_BOOKING_LIMIT_REACHED"
    CUSTOMER_TIME_CONFLICT = "CUSTOMER_TIME_CONFLICT"
    APPOINTMENT_NOT_FOUND = "APPOINTMENT_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INVALID_APPOINTMENT_STATUS_TRANSITION = "INVALID_APPOINTMENT_STATUS_TRANSITION"
    CANCELLATION_WINDOW_CLOSED = "CANCELLATION_WINDOW_CLOSED"
    RESCHEDULE_NOT_ALLOWED = "RESCHEDULE_NOT_ALLOWED"
    CASH_SHIFT_REQUIRED = "CASH_SHIFT_REQUIRED"
    CASH_SHIFT_ALREADY_OPEN = "CASH_SHIFT_ALREADY_OPEN"
    CASH_SHIFT_NOT_OPEN = "CASH_SHIFT_NOT_OPEN"
    PAYMENT_EXCEEDS_OUTSTANDING_AMOUNT = "PAYMENT_EXCEEDS_OUTSTANDING_AMOUNT"
    REFUND_EXCEEDS_REFUNDABLE_AMOUNT = "REFUND_EXCEEDS_REFUNDABLE_AMOUNT"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TELEGRAM_INIT_DATA = "INVALID_TELEGRAM_INIT_DATA"
    STAFF_NOT_BOUND = "STAFF_NOT_BOUND"
    CUSTOMER_BLOCKED = "CUSTOMER_BLOCKED"
    INVALID_BIND_CODE = "INVALID_BIND_CODE"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"


_DEFAULT_DETAILS: Final[dict[BookingErrorCode, str]] = {
    BookingErrorCode.SLOT_TAKEN: "The selected time is no longer available.",
    BookingErrorCode.HOLD_EXPIRED: "The temporary reservation has expired.",
    BookingErrorCode.HOLD_NOT_FOUND: "The temporary reservation was not found.",
    BookingErrorCode.HOLD_OWNER_MISMATCH: "The temporary reservation belongs to another customer.",
    BookingErrorCode.OUTSIDE_WORKING_HOURS: "The requested time is outside working hours.",
    BookingErrorCode.SERVICE_INACTIVE: "The service is unavailable.",
    BookingErrorCode.SPECIALIST_INACTIVE: "The specialist is unavailable.",
    BookingErrorCode.SPECIALIST_DOES_NOT_PROVIDE_SERVICE: (
        "The specialist does not provide service."
    ),
    BookingErrorCode.SPECIALIST_UNAVAILABLE: "The specialist is unavailable at that time.",
    BookingErrorCode.BRANCH_INACTIVE: "The branch is unavailable.",
    BookingErrorCode.BOOKING_TOO_EARLY: "The requested time is too soon.",
    BookingErrorCode.BOOKING_TOO_FAR_IN_FUTURE: "The requested time is too far in the future.",
    BookingErrorCode.CUSTOMER_BOOKING_LIMIT_REACHED: "The customer has reached the booking limit.",
    BookingErrorCode.CUSTOMER_TIME_CONFLICT: "The customer has an overlapping appointment.",
    BookingErrorCode.APPOINTMENT_NOT_FOUND: "The appointment was not found.",
    BookingErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    BookingErrorCode.INVALID_APPOINTMENT_STATUS_TRANSITION: (
        "The appointment transition is invalid."
    ),
    BookingErrorCode.CANCELLATION_WINDOW_CLOSED: "The client cancellation window has closed.",
    BookingErrorCode.RESCHEDULE_NOT_ALLOWED: "The appointment cannot be rescheduled.",
    BookingErrorCode.CASH_SHIFT_REQUIRED: "An open cash shift is required.",
    BookingErrorCode.CASH_SHIFT_ALREADY_OPEN: "A cash shift is already open.",
    BookingErrorCode.CASH_SHIFT_NOT_OPEN: "There is no open cash shift.",
    BookingErrorCode.PAYMENT_EXCEEDS_OUTSTANDING_AMOUNT: (
        "The payment exceeds the outstanding amount."
    ),
    BookingErrorCode.REFUND_EXCEEDS_REFUNDABLE_AMOUNT: "The refund exceeds the refundable amount.",
    BookingErrorCode.CURRENCY_MISMATCH: "The currency does not match.",
    BookingErrorCode.INSUFFICIENT_STOCK: "There is insufficient stock.",
    BookingErrorCode.IDEMPOTENCY_CONFLICT: "The idempotency key conflicts with another request.",
    BookingErrorCode.FORBIDDEN: "You are not allowed to perform this operation.",
    BookingErrorCode.INVALID_TELEGRAM_INIT_DATA: "Telegram authentication data is invalid.",
    BookingErrorCode.STAFF_NOT_BOUND: "The staff Telegram account is not bound.",
    BookingErrorCode.CUSTOMER_BLOCKED: "The customer is blocked.",
    BookingErrorCode.INVALID_BIND_CODE: "The bind code is invalid or expired.",
    BookingErrorCode.RATE_LIMITED: "Too many requests were received.",
    BookingErrorCode.INVALID_REQUEST: "The request is invalid.",
}


class BookingDomainError(Exception):
    """Expected pure-domain failure with a stable code and no transport detail."""

    def __init__(self, code: BookingErrorCode, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail or _DEFAULT_DETAILS[code]
        super().__init__(self.detail)


def require(condition: bool, code: BookingErrorCode, detail: str | None = None) -> None:
    """Raise an intentional booking failure when one invariant is false."""

    if not condition:
        raise BookingDomainError(code, detail)
