"""Immutable Finance result DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.finance.domain.enums import EntryDirection, EntryKind


@dataclass(frozen=True, slots=True)
class WorkspaceResult:
    id: UUID
    name: str
    default_currency: str


@dataclass(frozen=True, slots=True)
class AccountResult:
    id: UUID
    name: str
    currency: str
    color: str | None
    is_archived: bool
    balance: Decimal


@dataclass(frozen=True, slots=True)
class CategoryResult:
    id: UUID
    name: str
    direction: EntryDirection
    icon: str | None
    is_archived: bool


@dataclass(frozen=True, slots=True)
class EntryResult:
    id: UUID
    account_id: UUID
    account_name: str
    category_id: UUID | None
    category_name: str | None
    direction: EntryDirection
    kind: EntryKind
    amount: Decimal
    currency: str
    occurred_at: datetime
    note: str | None
    reversal_of_id: UUID | None
    transfer_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EntryPage:
    items: tuple[EntryResult, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class TransferResult:
    transfer_id: UUID
    source_entry: EntryResult
    destination_entry: EntryResult


@dataclass(frozen=True, slots=True)
class CurrencySummary:
    currency: str
    balance: Decimal
    income: Decimal
    expense: Decimal
