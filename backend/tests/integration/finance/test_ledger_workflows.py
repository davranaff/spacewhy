"""Real PostgreSQL verification for Finance reversal and transfer workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from pydantic import SecretStr

from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.modules.finance.application.service import FinanceService
from app.modules.finance.domain.enums import EntryDirection, EntryKind
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transfer_and_reversal_keep_balances_consistent(test_database_url: str) -> None:
    database = Database(DatabaseSettings(url=SecretStr(test_database_url)))
    database.initialize()
    principal_id = uuid4()
    workspace_id: UUID | None = None
    service = FinanceService(database=database)

    try:
        workspace = await service.bootstrap_workspace(
            principal_id=principal_id,
            workspace_name="Integration finances",
            default_currency="UZS",
            account_name="Main",
            initial_balance=Decimal("0"),
            request_id="integration-bootstrap",
        )
        workspace_id = workspace.id
        main_account = (await service.list_accounts(principal_id=principal_id))[0]
        savings_account = await service.create_account(
            principal_id=principal_id,
            name="Savings",
            currency="UZS",
            color=None,
            request_id="integration-account",
        )
        income_category = next(
            category
            for category in await service.list_categories(principal_id=principal_id)
            if category.direction is EntryDirection.INCOME
        )
        income = await service.create_entry(
            principal_id=principal_id,
            account_id=main_account.id,
            category_id=income_category.id,
            direction=EntryDirection.INCOME,
            amount=Decimal("100000"),
            currency="UZS",
            occurred_at=datetime(2026, 8, 21, 10, tzinfo=UTC),
            note="Salary",
            idempotency_key="integration-income",
            request_id="integration-income",
        )

        transfer = await service.create_transfer(
            principal_id=principal_id,
            source_account_id=main_account.id,
            destination_account_id=savings_account.id,
            amount=Decimal("25000"),
            currency="UZS",
            occurred_at=datetime(2026, 8, 21, 11, tzinfo=UTC),
            note=None,
            idempotency_key="integration-transfer",
            request_id="integration-transfer",
        )
        transfer_replay = await service.create_transfer(
            principal_id=principal_id,
            source_account_id=main_account.id,
            destination_account_id=savings_account.id,
            amount=Decimal("25000"),
            currency="UZS",
            occurred_at=datetime(2026, 8, 21, 11, tzinfo=UTC),
            note=None,
            idempotency_key="integration-transfer",
            request_id="integration-transfer-replay",
        )
        reversal = await service.reverse_entry(
            principal_id=principal_id,
            entry_id=income.id,
            idempotency_key="integration-reversal",
            request_id="integration-reversal",
        )
        reversal_replay = await service.reverse_entry(
            principal_id=principal_id,
            entry_id=income.id,
            idempotency_key="integration-reversal",
            request_id="integration-reversal-replay",
        )

        assert transfer.source_entry.kind is EntryKind.TRANSFER
        assert transfer.destination_entry.kind is EntryKind.TRANSFER
        assert transfer_replay == transfer
        assert reversal.kind is EntryKind.REVERSAL
        assert reversal.reversal_of_id == income.id
        assert reversal_replay == reversal
        balances = {
            account.name: account.balance
            for account in await service.list_accounts(principal_id=principal_id)
        }
        assert balances == {"Main": Decimal("-25000.00"), "Savings": Decimal("25000.00")}
        summaries = await service.summary(principal_id=principal_id)
        assert len(summaries) == 1
        assert summaries[0].balance == Decimal("0.00")
        assert summaries[0].income == Decimal("0.00")
        assert summaries[0].expense == Decimal("0.00")
    finally:
        if workspace_id is not None:
            async with database.session() as session, session.begin():
                await session.execute(
                    sa.delete(FinanceOutbox).where(FinanceOutbox.workspace_id == workspace_id)
                )
                await session.execute(
                    sa.delete(FinanceAudit).where(FinanceAudit.workspace_id == workspace_id)
                )
                await session.execute(
                    sa.delete(FinanceIdempotency).where(
                        FinanceIdempotency.workspace_id == workspace_id
                    )
                )
                await session.execute(
                    sa.delete(FinanceEntry).where(FinanceEntry.workspace_id == workspace_id)
                )
                await session.execute(
                    sa.delete(FinanceCategory).where(FinanceCategory.workspace_id == workspace_id)
                )
                await session.execute(
                    sa.delete(FinanceAccount).where(FinanceAccount.workspace_id == workspace_id)
                )
                await session.execute(
                    sa.delete(FinanceMembership).where(
                        FinanceMembership.workspace_id == workspace_id
                    )
                )
                await session.execute(
                    sa.delete(FinanceWorkspace).where(FinanceWorkspace.id == workspace_id)
                )
        await database.dispose()
