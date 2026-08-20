"""Stable identity failures without transport coupling."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class IdentityErrorCode(StrEnum):
    """Machine-readable Identity API outcomes."""

    ENROLLMENT_REQUIRED = "IDENTITY_ENROLLMENT_REQUIRED"
    CHALLENGE_INVALID_OR_EXPIRED = "IDENTITY_CHALLENGE_INVALID_OR_EXPIRED"
    CHALLENGE_ATTEMPTS_EXHAUSTED = "IDENTITY_CHALLENGE_ATTEMPTS_EXHAUSTED"
    INVALID_TELEGRAM_CONTACT = "IDENTITY_INVALID_TELEGRAM_CONTACT"
    INVALID_TELEGRAM_INIT_DATA = "IDENTITY_INVALID_TELEGRAM_INIT_DATA"
    PHONE_ALREADY_BOUND = "IDENTITY_PHONE_ALREADY_BOUND"
    SESSION_INVALID = "IDENTITY_SESSION_INVALID"
    RATE_LIMITED = "IDENTITY_RATE_LIMITED"
    INVALID_REQUEST = "IDENTITY_INVALID_REQUEST"


_DETAILS: Final[dict[IdentityErrorCode, str]] = {
    IdentityErrorCode.ENROLLMENT_REQUIRED: "Telegram enrollment is required.",
    IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED: "The challenge is invalid or expired.",
    IdentityErrorCode.CHALLENGE_ATTEMPTS_EXHAUSTED: "The challenge attempt limit was reached.",
    IdentityErrorCode.INVALID_TELEGRAM_CONTACT: "The Telegram contact is invalid.",
    IdentityErrorCode.INVALID_TELEGRAM_INIT_DATA: "Telegram authentication data is invalid.",
    IdentityErrorCode.PHONE_ALREADY_BOUND: "The phone is already bound to another account.",
    IdentityErrorCode.SESSION_INVALID: "The session is invalid or expired.",
    IdentityErrorCode.RATE_LIMITED: "Too many requests were received.",
    IdentityErrorCode.INVALID_REQUEST: "The request is invalid.",
}


class IdentityDomainError(Exception):
    """Expected identity failure safe to map at the HTTP boundary."""

    def __init__(self, code: IdentityErrorCode, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail or _DETAILS[code]
        super().__init__(self.detail)
