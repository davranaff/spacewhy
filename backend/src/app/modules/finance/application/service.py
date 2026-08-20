"""Scoped Finance commands and queries."""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.finance.application.dto import (
    AccountResult,
    CategoryResult,
    CurrencySummary,
    EntryPage,
    EntryResult,
    WorkspaceResult,
)
from app.modules.finance.domain.enums import EntryDirection, EntryKind, WorkspaceRole
from app.modules.finance.domain.errors import FinanceDomainError, FinanceErrorCode
from app.modules.finance.domain.policies import validate_amount, validate_currency
from app.modules.finance.infrastructure.persistence.models import (
    FinanceAccount,
    FinanceAudit,
    FinanceCategory,
    FinanceEntry,
    FinanceIdempotency,
    FinanceMembership,
    FinanceOutbox,
    FinanceWorkspace,
)

_DEFAULT_CATEGORIES: tuple[tuple[EntryDirection, str, str], ...] = (
    (EntryDirection.INCOME, "Salary", "wallet"),
    (EntryDirection.INCOME, "Other income", "plus"),
    (EntryDirection.EXPENSE, "Food", "restaurant"),
    (EntryDirection.EXPENSE, "Transport", "car"),
    (EntryDirection.EXPENSE, "Home", "home"),
    (EntryDirection.EXPENSE, "Health", "health"),
    (EntryDirection.EXPENSE, "Other expense", "dots"),
)


class FinanceService:
    """Own the personal workspace and append-only ledger vertical slice."""

    def __init__(self, *, database: Database, clock: Clock | None = None) -> None:
        self._database = database
        self._clock = clock or SystemClock()

    async def bootstrap_workspace(
        self,
        *,
        principal_id: UUID,
        workspace_name: str,
        default_currency: str,
        account_name: str,
        initial_balance: Decimal,
        request_id: str | None,
    ) -> WorkspaceResult:
        """Create one personal workspace idempotently with defaults and opening balance."""

        currency = validate_currency(default_currency)
        if initial_balance < 0:
            raise FinanceDomainError(FinanceErrorCode.INVALID_REQUEST)
        if initial_balance:
            validate_amount(initial_balance)
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            await session.execute(
                sa.select(
                    sa.func.pg_advisory_xact_lock(
                        sa.func.hashtext(f"finance:bootstrap:{principal_id}")
                    )
                )
            )
            existing = await session.scalar(
                sa.select(FinanceMembership).where(
                    FinanceMembership.principal_id == principal_id,
                    FinanceMembership.is_active.is_(True),
                )
            )
            if existing is not None:
                workspace = await session.get(FinanceWorkspace, existing.workspace_id)
                if workspace is None:
                    raise FinanceDomainError(FinanceErrorCode.MEMBERSHIP_REQUIRED)
                return _workspace_result(workspace)
            workspace = FinanceWorkspace(
                name=workspace_name.strip(),
                default_currency=currency,
                is_active=True,
            )
            session.add(workspace)
            await session.flush()
            session.add(
                FinanceMembership(
                    workspace_id=workspace.id,
                    principal_id=principal_id,
                    role=WorkspaceRole.OWNER,
                    is_active=True,
                )
            )
            account = FinanceAccount(
                workspace_id=workspace.id,
                name=account_name.strip(),
                currency=currency,
                color="#7C5CFC",
            )
            session.add(account)
            categories = [
                FinanceCategory(
                    workspace_id=workspace.id,
                    direction=direction,
                    name=name,
                    icon=icon,
                    is_system=True,
                )
                for direction, name, icon in _DEFAULT_CATEGORIES
            ]
            session.add_all(categories)
            await session.flush()
            if initial_balance:
                opening = FinanceEntry(
                    workspace_id=workspace.id,
                    account_id=account.id,
                    category_id=None,
                    direction=EntryDirection.INCOME,
                    kind=EntryKind.OPENING_BALANCE,
                    amount=initial_balance,
                    currency=currency,
                    occurred_at=now,
                    note="Opening balance",
                    created_by_principal_id=principal_id,
                )
                session.add(opening)
            session.add(
                FinanceAudit(
                    workspace_id=workspace.id,
                    principal_id=principal_id,
                    action="workspace_bootstrapped",
                    request_id=request_id,
                    metadata_json={"currency": currency},
                )
            )
        return _workspace_result(workspace)

    async def create_account(
        self,
        *,
        principal_id: UUID,
        name: str,
        currency: str,
        color: str | None,
        request_id: str | None,
    ) -> AccountResult:
        normalized_currency = validate_currency(currency)
        async with self._database.session() as session, session.begin():
            workspace_id = await self._workspace_id(session, principal_id)
            account = FinanceAccount(
                workspace_id=workspace_id,
                name=name.strip(),
                currency=normalized_currency,
                color=color,
            )
            session.add(account)
            await session.flush()
            session.add(
                FinanceAudit(
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    action="account_created",
                    resource_id=account.id,
                    request_id=request_id,
                    metadata_json={"currency": normalized_currency},
                )
            )
        return AccountResult(
            id=account.id,
            name=account.name,
            currency=account.currency,
            color=account.color,
            is_archived=account.is_archived,
            balance=Decimal("0"),
        )

    async def list_accounts(self, *, principal_id: UUID) -> tuple[AccountResult, ...]:
        async with self._database.session() as session:
            workspace_id = await self._workspace_id(session, principal_id)
            signed_amount = sa.case(
                (FinanceEntry.direction == EntryDirection.INCOME, FinanceEntry.amount),
                else_=-FinanceEntry.amount,
            )
            rows = (
                await session.execute(
                    sa.select(FinanceAccount, sa.func.coalesce(sa.func.sum(signed_amount), 0))
                    .outerjoin(FinanceEntry, FinanceEntry.account_id == FinanceAccount.id)
                    .where(FinanceAccount.workspace_id == workspace_id)
                    .group_by(FinanceAccount.id)
                    .order_by(
                        FinanceAccount.is_archived, FinanceAccount.created_at, FinanceAccount.id
                    )
                )
            ).all()
        return tuple(
            AccountResult(
                id=account.id,
                name=account.name,
                currency=account.currency,
                color=account.color,
                is_archived=account.is_archived,
                balance=Decimal(balance),
            )
            for account, balance in rows
        )

    async def list_categories(self, *, principal_id: UUID) -> tuple[CategoryResult, ...]:
        async with self._database.session() as session:
            workspace_id = await self._workspace_id(session, principal_id)
            categories = (
                await session.scalars(
                    sa.select(FinanceCategory)
                    .where(FinanceCategory.workspace_id == workspace_id)
                    .order_by(
                        FinanceCategory.direction,
                        FinanceCategory.is_archived,
                        FinanceCategory.name,
                        FinanceCategory.id,
                    )
                )
            ).all()
        return tuple(_category_result(category) for category in categories)

    async def create_entry(
        self,
        *,
        principal_id: UUID,
        account_id: UUID,
        category_id: UUID,
        direction: EntryDirection,
        amount: Decimal,
        currency: str,
        occurred_at: datetime,
        note: str | None,
        idempotency_key: str,
        request_id: str | None,
    ) -> EntryResult:
        """Append one income/expense with scoped replay protection, audit, and outbox."""

        validated_amount = validate_amount(amount)
        normalized_currency = validate_currency(currency)
        fingerprint = _fingerprint(
            {
                "account_id": str(account_id),
                "category_id": str(category_id),
                "direction": direction.value,
                "amount": str(validated_amount),
                "currency": normalized_currency,
                "occurred_at": occurred_at.isoformat(),
                "note": note,
            }
        )
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            workspace_id = await self._workspace_id(session, principal_id)
            lock_key = (
                f"finance:idempotency:{workspace_id}:{principal_id}:create_entry:{idempotency_key}"
            )
            await session.execute(
                sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key)))
            )
            replay = await session.scalar(
                sa.select(FinanceIdempotency).where(
                    FinanceIdempotency.workspace_id == workspace_id,
                    FinanceIdempotency.principal_id == principal_id,
                    FinanceIdempotency.operation == "create_entry",
                    FinanceIdempotency.key == idempotency_key,
                )
            )
            if replay is not None:
                if replay.request_fingerprint != fingerprint:
                    raise FinanceDomainError(FinanceErrorCode.IDEMPOTENCY_CONFLICT)
                return await self._entry_result(session, workspace_id, replay.response_entry_id)
            account = await session.scalar(
                sa.select(FinanceAccount).where(
                    FinanceAccount.id == account_id,
                    FinanceAccount.workspace_id == workspace_id,
                )
            )
            if account is None:
                raise FinanceDomainError(FinanceErrorCode.ACCOUNT_NOT_FOUND)
            if account.is_archived:
                raise FinanceDomainError(FinanceErrorCode.ACCOUNT_ARCHIVED)
            if account.currency != normalized_currency:
                raise FinanceDomainError(FinanceErrorCode.CURRENCY_MISMATCH)
            category = await session.scalar(
                sa.select(FinanceCategory).where(
                    FinanceCategory.id == category_id,
                    FinanceCategory.workspace_id == workspace_id,
                    FinanceCategory.is_archived.is_(False),
                )
            )
            if category is None:
                raise FinanceDomainError(FinanceErrorCode.CATEGORY_NOT_FOUND)
            if category.direction is not direction:
                raise FinanceDomainError(FinanceErrorCode.CATEGORY_DIRECTION_MISMATCH)
            entry = FinanceEntry(
                workspace_id=workspace_id,
                account_id=account.id,
                category_id=category.id,
                direction=direction,
                kind=EntryKind.STANDARD,
                amount=validated_amount,
                currency=normalized_currency,
                occurred_at=occurred_at,
                note=note.strip() if note else None,
                created_by_principal_id=principal_id,
            )
            session.add(entry)
            await session.flush()
            session.add(
                FinanceIdempotency(
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    operation="create_entry",
                    key=idempotency_key,
                    request_fingerprint=fingerprint,
                    response_entry_id=entry.id,
                )
            )
            session.add(
                FinanceAudit(
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    action="entry_created",
                    resource_id=entry.id,
                    request_id=request_id,
                    metadata_json={"direction": direction.value, "currency": normalized_currency},
                )
            )
            session.add(
                FinanceOutbox(
                    workspace_id=workspace_id,
                    event_type="finance.entry.created",
                    event_version=1,
                    aggregate_id=entry.id,
                    payload={
                        "entry_id": str(entry.id),
                        "workspace_id": str(workspace_id),
                        "direction": direction.value,
                        "amount": str(validated_amount),
                        "currency": normalized_currency,
                    },
                    occurred_at=now,
                )
            )
            await session.flush()
            result = EntryResult(
                id=entry.id,
                account_id=account.id,
                account_name=account.name,
                category_id=category.id,
                category_name=category.name,
                direction=entry.direction,
                kind=entry.kind,
                amount=entry.amount,
                currency=entry.currency,
                occurred_at=entry.occurred_at,
                note=entry.note,
                created_at=entry.created_at,
            )
        return result

    async def list_entries(
        self,
        *,
        principal_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> EntryPage:
        cursor_value = _decode_cursor(cursor) if cursor else None
        async with self._database.session() as session:
            workspace_id = await self._workspace_id(session, principal_id)
            statement = (
                sa.select(FinanceEntry, FinanceAccount.name, FinanceCategory.name)
                .join(FinanceAccount, FinanceAccount.id == FinanceEntry.account_id)
                .outerjoin(FinanceCategory, FinanceCategory.id == FinanceEntry.category_id)
                .where(FinanceEntry.workspace_id == workspace_id)
                .order_by(FinanceEntry.occurred_at.desc(), FinanceEntry.id.desc())
                .limit(limit + 1)
            )
            if cursor_value is not None:
                cursor_time, cursor_id = cursor_value
                statement = statement.where(
                    (FinanceEntry.occurred_at < cursor_time)
                    | ((FinanceEntry.occurred_at == cursor_time) & (FinanceEntry.id < cursor_id))
                )
            rows = (await session.execute(statement)).all()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = tuple(_entry_row_result(row) for row in page_rows)
        next_cursor = (
            _encode_cursor(page_rows[-1][0].occurred_at, page_rows[-1][0].id)
            if has_more and page_rows
            else None
        )
        return EntryPage(items=items, next_cursor=next_cursor)

    async def summary(self, *, principal_id: UUID) -> tuple[CurrencySummary, ...]:
        async with self._database.session() as session:
            workspace_id = await self._workspace_id(session, principal_id)
            income = sa.func.coalesce(
                sa.func.sum(
                    sa.case(
                        (FinanceEntry.direction == EntryDirection.INCOME, FinanceEntry.amount),
                        else_=0,
                    )
                ),
                0,
            )
            expense = sa.func.coalesce(
                sa.func.sum(
                    sa.case(
                        (FinanceEntry.direction == EntryDirection.EXPENSE, FinanceEntry.amount),
                        else_=0,
                    )
                ),
                0,
            )
            rows = (
                await session.execute(
                    sa.select(FinanceEntry.currency, income, expense)
                    .where(FinanceEntry.workspace_id == workspace_id)
                    .group_by(FinanceEntry.currency)
                    .order_by(FinanceEntry.currency)
                )
            ).all()
        return tuple(
            CurrencySummary(
                currency=currency,
                balance=Decimal(income_value) - Decimal(expense_value),
                income=Decimal(income_value),
                expense=Decimal(expense_value),
            )
            for currency, income_value, expense_value in rows
        )

    async def _workspace_id(self, session: AsyncSession, principal_id: UUID) -> UUID:
        membership = await session.scalar(
            sa.select(FinanceMembership).where(
                FinanceMembership.principal_id == principal_id,
                FinanceMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise FinanceDomainError(FinanceErrorCode.MEMBERSHIP_REQUIRED)
        workspace_active = await session.scalar(
            sa.select(FinanceWorkspace.is_active).where(
                FinanceWorkspace.id == membership.workspace_id
            )
        )
        if not workspace_active:
            raise FinanceDomainError(FinanceErrorCode.MEMBERSHIP_REQUIRED)
        return membership.workspace_id

    async def _entry_result(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        entry_id: UUID,
    ) -> EntryResult:
        row = (
            await session.execute(
                sa.select(FinanceEntry, FinanceAccount.name, FinanceCategory.name)
                .join(FinanceAccount, FinanceAccount.id == FinanceEntry.account_id)
                .outerjoin(FinanceCategory, FinanceCategory.id == FinanceEntry.category_id)
                .where(
                    FinanceEntry.workspace_id == workspace_id,
                    FinanceEntry.id == entry_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise FinanceDomainError(FinanceErrorCode.IDEMPOTENCY_CONFLICT)
        return _entry_row_result(row)


def _workspace_result(value: FinanceWorkspace) -> WorkspaceResult:
    return WorkspaceResult(
        id=value.id,
        name=value.name,
        default_currency=value.default_currency,
    )


def _category_result(value: FinanceCategory) -> CategoryResult:
    return CategoryResult(
        id=value.id,
        name=value.name,
        direction=value.direction,
        icon=value.icon,
        is_archived=value.is_archived,
    )


def _entry_row_result(row: Sequence[object]) -> EntryResult:
    entry = row[0]
    if not isinstance(entry, FinanceEntry):
        raise TypeError("Finance entry row is invalid.")
    account_name = row[1]
    category_name = row[2]
    if not isinstance(account_name, str) or not (
        category_name is None or isinstance(category_name, str)
    ):
        raise TypeError("Finance entry row is invalid.")
    return EntryResult(
        id=entry.id,
        account_id=entry.account_id,
        account_name=account_name,
        category_id=entry.category_id,
        category_name=category_name,
        direction=entry.direction,
        kind=entry.kind,
        amount=entry.amount,
        currency=entry.currency,
        occurred_at=entry.occurred_at,
        note=entry.note,
        created_at=entry.created_at,
    )


def _fingerprint(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode()).hexdigest()


def _encode_cursor(occurred_at: datetime, entry_id: UUID) -> str:
    value = json.dumps([occurred_at.isoformat(), str(entry_id)], separators=(",", ":"))
    return base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()


def _decode_cursor(value: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        decoded: object = json.loads(raw)
        if not isinstance(decoded, list):
            raise ValueError
        values = cast(list[object], decoded)
        if len(values) != 2:
            raise ValueError
        raw_time, raw_id = values
        if not isinstance(raw_time, str) or not isinstance(raw_id, str):
            raise ValueError
        occurred_at = datetime.fromisoformat(raw_time)
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError
        return occurred_at, UUID(raw_id)
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise FinanceDomainError(FinanceErrorCode.CURSOR_INVALID) from error
