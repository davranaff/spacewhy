"""Stable Finance failures without HTTP coupling."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class FinanceErrorCode(StrEnum):
    MEMBERSHIP_REQUIRED = "FINANCE_MEMBERSHIP_REQUIRED"
    PERMISSION_DENIED = "FINANCE_PERMISSION_DENIED"
    ACCOUNT_NOT_FOUND = "FINANCE_ACCOUNT_NOT_FOUND"
    ACCOUNT_ARCHIVED = "FINANCE_ACCOUNT_ARCHIVED"
    CATEGORY_NOT_FOUND = "FINANCE_CATEGORY_NOT_FOUND"
    CATEGORY_DIRECTION_MISMATCH = "FINANCE_CATEGORY_DIRECTION_MISMATCH"
    ENTRY_NOT_FOUND = "FINANCE_ENTRY_NOT_FOUND"
    ENTRY_NOT_REVERSIBLE = "FINANCE_ENTRY_NOT_REVERSIBLE"
    ENTRY_ALREADY_REVERSED = "FINANCE_ENTRY_ALREADY_REVERSED"
    TRANSFER_SAME_ACCOUNT = "FINANCE_TRANSFER_SAME_ACCOUNT"
    CURRENCY_MISMATCH = "FINANCE_CURRENCY_MISMATCH"
    IDEMPOTENCY_CONFLICT = "FINANCE_IDEMPOTENCY_CONFLICT"
    CURSOR_INVALID = "FINANCE_CURSOR_INVALID"
    INVALID_REQUEST = "FINANCE_INVALID_REQUEST"


_DETAILS: Final[dict[FinanceErrorCode, str]] = {
    FinanceErrorCode.MEMBERSHIP_REQUIRED: "An active Finance workspace is required.",
    FinanceErrorCode.PERMISSION_DENIED: "You are not allowed to perform this operation.",
    FinanceErrorCode.ACCOUNT_NOT_FOUND: "The account was not found.",
    FinanceErrorCode.ACCOUNT_ARCHIVED: "The account is archived.",
    FinanceErrorCode.CATEGORY_NOT_FOUND: "The category was not found.",
    FinanceErrorCode.CATEGORY_DIRECTION_MISMATCH: "The category direction does not match.",
    FinanceErrorCode.ENTRY_NOT_FOUND: "The finance entry was not found.",
    FinanceErrorCode.ENTRY_NOT_REVERSIBLE: "The finance entry cannot be reversed.",
    FinanceErrorCode.ENTRY_ALREADY_REVERSED: "The finance entry was already reversed.",
    FinanceErrorCode.TRANSFER_SAME_ACCOUNT: "Transfer accounts must be different.",
    FinanceErrorCode.CURRENCY_MISMATCH: "The currency does not match the account.",
    FinanceErrorCode.IDEMPOTENCY_CONFLICT: "The idempotency key conflicts with another request.",
    FinanceErrorCode.CURSOR_INVALID: "The page cursor is invalid.",
    FinanceErrorCode.INVALID_REQUEST: "The finance request is invalid.",
}


class FinanceDomainError(Exception):
    def __init__(self, code: FinanceErrorCode, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail or _DETAILS[code]
        super().__init__(self.detail)
