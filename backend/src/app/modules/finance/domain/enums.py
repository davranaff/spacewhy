"""Durable Finance enum values."""

from enum import StrEnum


class EntryDirection(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class EntryKind(StrEnum):
    STANDARD = "standard"
    OPENING_BALANCE = "opening_balance"
    REVERSAL = "reversal"
    TRANSFER = "transfer"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"
