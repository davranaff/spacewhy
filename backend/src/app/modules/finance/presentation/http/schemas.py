"""Strict Finance transport schemas."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.finance.application.dto import (
    AccountResult,
    CategoryResult,
    CurrencySummary,
    EntryPage,
    EntryResult,
    TransferResult,
    WorkspaceResult,
)
from app.modules.finance.domain.enums import EntryDirection, EntryKind


class _Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BootstrapRequest(_Schema):
    workspace_name: str = Field(default="My finances", min_length=1, max_length=160)
    default_currency: str = Field(default="UZS", pattern=r"^[A-Za-z]{3}$")
    account_name: str = Field(default="Main account", min_length=1, max_length=120)
    initial_balance: Decimal = Field(default=Decimal("0"), max_digits=18, decimal_places=2, ge=0)


class WorkspaceResponse(_Schema):
    id: UUID
    name: str
    default_currency: str

    @classmethod
    def from_result(cls, value: WorkspaceResult) -> WorkspaceResponse:
        return cls(**asdict(value))


class CreateAccountRequest(_Schema):
    name: str = Field(min_length=1, max_length=120)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    color: str | None = Field(default=None, max_length=16)


class AccountResponse(_Schema):
    id: UUID
    name: str
    currency: str
    color: str | None
    is_archived: bool
    balance: Decimal

    @classmethod
    def from_result(cls, value: AccountResult) -> AccountResponse:
        return cls(**asdict(value))


class CategoryResponse(_Schema):
    id: UUID
    name: str
    direction: EntryDirection
    icon: str | None
    is_archived: bool

    @classmethod
    def from_result(cls, value: CategoryResult) -> CategoryResponse:
        return cls(**asdict(value))


class CreateEntryRequest(_Schema):
    account_id: UUID
    category_id: UUID
    direction: EntryDirection
    amount: Decimal = Field(max_digits=18, decimal_places=2, gt=0)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    occurred_at: datetime
    note: str | None = Field(default=None, max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class CreateTransferRequest(_Schema):
    source_account_id: UUID
    destination_account_id: UUID
    amount: Decimal = Field(max_digits=18, decimal_places=2, gt=0)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    occurred_at: datetime
    note: str | None = Field(default=None, max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class EntryResponse(_Schema):
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

    @classmethod
    def from_result(cls, value: EntryResult) -> EntryResponse:
        return cls(**asdict(value))


class EntryPageResponse(_Schema):
    items: list[EntryResponse]
    next_cursor: str | None

    @classmethod
    def from_result(cls, value: EntryPage) -> EntryPageResponse:
        return cls(
            items=[EntryResponse.from_result(item) for item in value.items],
            next_cursor=value.next_cursor,
        )


class TransferResponse(_Schema):
    transfer_id: UUID
    source_entry: EntryResponse
    destination_entry: EntryResponse

    @classmethod
    def from_result(cls, value: TransferResult) -> TransferResponse:
        return cls(
            transfer_id=value.transfer_id,
            source_entry=EntryResponse.from_result(value.source_entry),
            destination_entry=EntryResponse.from_result(value.destination_entry),
        )


class CurrencySummaryResponse(_Schema):
    currency: str
    balance: Decimal
    income: Decimal
    expense: Decimal

    @classmethod
    def from_result(cls, value: CurrencySummary) -> CurrencySummaryResponse:
        return cls(**asdict(value))


class SummaryResponse(_Schema):
    currencies: list[CurrencySummaryResponse]
