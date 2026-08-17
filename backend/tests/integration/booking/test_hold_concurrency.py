"""PostgreSQL-only concurrency coverage for the booking source-of-truth hold invariant."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from pydantic import SecretStr

from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import HoldCommand, HoldResult
from app.modules.booking.application.service import BookingService
from app.modules.booking.domain.enums import AccessRole, ActorType
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.infrastructure.persistence.models import (
    BookingBranch,
    BookingOrganization,
    BookingSettings,
    Customer,
    Specialist,
    SpecialistService,
    WorkingSchedule,
)
from app.modules.booking.infrastructure.persistence.models import (
    BookingService as BookingServiceModel,
)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
_NOW = datetime(2026, 1, 5, 8, tzinfo=UTC)
_STARTS_AT = datetime(2026, 1, 5, 9, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FixedClock:
    """Inject a deterministic UTC clock into the real transactional booking service."""

    def now(self) -> datetime:
        """Return the shared test instant."""

        return _NOW


@dataclass(frozen=True, slots=True)
class BookingFixture:
    """Only opaque IDs needed to exercise two independently authenticated customers."""

    organization_id: UUID
    branch_id: UUID
    service_id: UUID
    specialist_id: UUID
    first_customer_id: UUID
    second_customer_id: UUID


def _upgrade_booking_schema(database_url: str) -> None:
    """Make this optional integration test independently runnable, not order-dependent."""

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE__URL": database_url},
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


async def _seed(database: Database) -> BookingFixture:
    """Create a self-contained tenant graph that has exactly one available specialist slot."""

    async with database.session() as session, session.begin():
        organization = BookingOrganization(
            slug=f"hold-concurrency-{uuid4().hex[:12]}",
            name="Hold concurrency tenant",
            default_timezone="UTC",
        )
        session.add(organization)
        await session.flush()
        branch = BookingBranch(organization_id=organization.id, name="Main", timezone="UTC")
        service = BookingServiceModel(
            organization_id=organization.id,
            name="Consultation",
            default_duration_minutes=30,
            default_price=Decimal("100.00"),
            currency="UZS",
        )
        specialist = Specialist(
            organization_id=organization.id,
            display_name="Specialist",
        )
        first_customer = Customer(organization_id=organization.id, first_name="First")
        second_customer = Customer(organization_id=organization.id, first_name="Second")
        session.add_all(
            (
                BookingSettings(organization_id=organization.id),
                branch,
                service,
                specialist,
                first_customer,
                second_customer,
            )
        )
        await session.flush()
        session.add_all(
            (
                SpecialistService(
                    organization_id=organization.id,
                    specialist_id=specialist.id,
                    service_id=service.id,
                    branch_id=branch.id,
                ),
                WorkingSchedule(
                    organization_id=organization.id,
                    specialist_id=specialist.id,
                    branch_id=branch.id,
                    weekday=_STARTS_AT.weekday(),
                    local_start_time=time(8),
                    local_end_time=time(18),
                ),
            )
        )
        return BookingFixture(
            organization_id=organization.id,
            branch_id=branch.id,
            service_id=service.id,
            specialist_id=specialist.id,
            first_customer_id=first_customer.id,
            second_customer_id=second_customer.id,
        )


def _customer_actor(organization_id: UUID, customer_id: UUID) -> BookingActor:
    """Construct the same least-privilege customer scope issued by verified Telegram auth."""

    return BookingActor(
        organization_id=organization_id,
        subject_id=customer_id,
        role=AccessRole.CUSTOMER,
        permissions=frozenset(),
        actor_type=ActorType.CUSTOMER,
        customer_id=customer_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_holds_for_one_busy_interval_allow_exactly_one(
    test_database_url: str,
) -> None:
    """Two client requests race through real locks and the exclusion constraint."""

    _upgrade_booking_schema(test_database_url)
    database = Database(DatabaseSettings(url=SecretStr(test_database_url)))
    database.initialize()
    fixture: BookingFixture | None = None
    try:
        fixture = await _seed(database)
        service = BookingService(database=database, clock=FixedClock())
        first = service.create_hold(
            actor=_customer_actor(fixture.organization_id, fixture.first_customer_id),
            command=HoldCommand(
                branch_id=fixture.branch_id,
                service_id=fixture.service_id,
                specialist_id=fixture.specialist_id,
                starts_at=_STARTS_AT,
                idempotency_key="concurrent-first",
            ),
        )
        second = service.create_hold(
            actor=_customer_actor(fixture.organization_id, fixture.second_customer_id),
            command=HoldCommand(
                branch_id=fixture.branch_id,
                service_id=fixture.service_id,
                specialist_id=fixture.specialist_id,
                starts_at=_STARTS_AT,
                idempotency_key="concurrent-second",
            ),
        )

        outcomes = await asyncio.gather(first, second, return_exceptions=True)
        successes = [outcome for outcome in outcomes if isinstance(outcome, HoldResult)]
        domain_errors = [outcome for outcome in outcomes if isinstance(outcome, BookingDomainError)]

        assert len(successes) == 1
        assert len(domain_errors) == 1
        assert domain_errors[0].code is BookingErrorCode.SLOT_TAKEN
        assert all(isinstance(outcome, HoldResult | BookingDomainError) for outcome in outcomes)
    finally:
        if fixture is not None:
            async with database.session() as session, session.begin():
                await session.execute(
                    sa.delete(BookingOrganization).where(
                        BookingOrganization.id == fixture.organization_id
                    )
                )
        await database.dispose()
