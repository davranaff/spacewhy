"""Polling worker for booking holds, durable notifications, and staff agendas."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.booking.application.access import BookingAccessService
from app.modules.booking.application.audit import append_audit_event
from app.modules.booking.application.permissions import PermissionCode
from app.modules.booking.domain.enums import (
    AccessScope,
    AppointmentStatus,
    OutboxStatus,
    ReservationStatus,
    ReservationType,
)
from app.modules.booking.domain.value_objects import require_aware
from app.modules.booking.infrastructure.persistence.models import (
    Appointment,
    BookingBranch,
    BookingMembership,
    BookingOrganization,
    BookingRole,
    BookingRoleAssignment,
    BookingRoleAssignmentBranch,
    BookingRolePermission,
    BookingSettings,
    Customer,
    CustomerIdentity,
    NotificationOutbox,
    SlotReservation,
    SpecialistService,
    StaffTelegramBinding,
    WorkingSchedule,
)

logger = logging.getLogger("spacewhy")

_DELIVERABLE_APPOINTMENT_STATUSES = frozenset(
    {
        AppointmentStatus.PENDING,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
    }
)


class PermanentNotificationDeliveryError(Exception):
    """A recipient or configuration condition that cannot succeed with a retry."""


class BookingNotificationDelivery(Protocol):
    """Deliver an already-localized booking outbox message through an app-bound channel."""

    async def deliver(
        self,
        *,
        bot_app_id: str,
        chat_id: str,
        locale: str,
        template_key: str,
        params: Mapping[str, object],
    ) -> None:
        """Deliver one message without retaining its private content."""


class BookingOutboxMetrics(Protocol):
    """Observe bounded worker health signals without recipient or message labels."""

    def record_booking_outbox_lag(self, *, lag_seconds: float) -> None:
        """Record how late a claimed notification was compared with its schedule."""


@dataclass(frozen=True, slots=True)
class _OutboxWorkItem:
    """A committed claim detached from ORM state before external I/O starts."""

    id: UUID
    organization_id: UUID
    appointment_id: UUID | None
    event_type: str
    recipient_type: str
    recipient_id: UUID | None
    bot_app_id: str
    chat_id: str | None
    locale: str
    template_key: str
    payload: Mapping[str, object]
    scheduled_at: datetime
    attempts: int
    max_attempts: int


@dataclass(frozen=True, slots=True)
class OutboxRunResult:
    """Safe aggregate worker outcome suitable for logs and operational checks."""

    expired_holds: int
    agendas_enqueued: int
    claimed: int
    delivered: int
    retried: int
    failed: int
    cancelled: int


class BookingOutboxWorker:
    """Process booking after-commit work with leases, retries, and pre-send guards."""

    def __init__(
        self,
        *,
        database: Database,
        access: BookingAccessService,
        delivery: BookingNotificationDelivery,
        poll_seconds: float,
        batch_size: int,
        lease_seconds: int,
        clock: Clock | None = None,
        metrics: BookingOutboxMetrics | None = None,
    ) -> None:
        self._database = database
        self._access = access
        self._delivery = delivery
        self._poll_seconds = poll_seconds
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds
        self._clock = clock or SystemClock()
        self._metrics = metrics

    async def run_forever(self, *, stop_event: asyncio.Event | None = None) -> None:
        """Poll until the process receives an explicit shutdown signal."""

        while stop_event is None or not stop_event.is_set():
            await self.run_once()
            if stop_event is None:
                await asyncio.sleep(self._poll_seconds)
                continue
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                continue

    async def run_once(self) -> OutboxRunResult:
        """Perform one bounded cleanup, agenda, claim, and delivery cycle."""

        now = require_aware(self._clock.now(), field_name="now")
        expired_holds = await self._expire_holds(now=now)
        agendas_enqueued = await self._enqueue_due_daily_agendas(now=now)
        work_items = await self._claim_due(now=now)
        delivered = 0
        retried = 0
        failed = 0
        cancelled = 0
        for work_item in work_items:
            if self._metrics is not None:
                self._metrics.record_booking_outbox_lag(
                    lag_seconds=max((now - work_item.scheduled_at).total_seconds(), 0.0)
                )
            if not await self._is_deliverable(work_item=work_item, now=now):
                await self._mark_cancelled(work_item_id=work_item.id)
                cancelled += 1
                continue
            if work_item.chat_id is None or not work_item.bot_app_id:
                await self._mark_cancelled(work_item_id=work_item.id)
                cancelled += 1
                continue
            try:
                await self._delivery.deliver(
                    bot_app_id=work_item.bot_app_id,
                    chat_id=work_item.chat_id,
                    locale=work_item.locale,
                    template_key=work_item.template_key,
                    params=work_item.payload,
                )
            except PermanentNotificationDeliveryError:
                await self._mark_failed(
                    work_item_id=work_item.id, reason="permanent_delivery_failure"
                )
                failed += 1
            except Exception:
                if await self._retry_or_fail(work_item=work_item, now=now):
                    retried += 1
                else:
                    failed += 1
            else:
                await self._mark_sent(work_item_id=work_item.id, now=now)
                delivered += 1
        result = OutboxRunResult(
            expired_holds=expired_holds,
            agendas_enqueued=agendas_enqueued,
            claimed=len(work_items),
            delivered=delivered,
            retried=retried,
            failed=failed,
            cancelled=cancelled,
        )
        if result.claimed or result.expired_holds or result.agendas_enqueued:
            logger.info(
                "booking_worker_cycle_completed",
                extra={
                    "expired_holds": result.expired_holds,
                    "agendas_enqueued": result.agendas_enqueued,
                    "claimed": result.claimed,
                    "delivered": result.delivered,
                    "retried": result.retried,
                    "failed": result.failed,
                    "cancelled": result.cancelled,
                },
            )
        return result

    async def _expire_holds(self, *, now: datetime) -> int:
        """Release abandoned holds so their exclusion constraints stop blocking new bookings."""

        async with self._database.session() as session, session.begin():
            result = await session.execute(
                sa.update(SlotReservation)
                .where(
                    SlotReservation.type == ReservationType.HOLD,
                    SlotReservation.status == ReservationStatus.ACTIVE,
                    SlotReservation.expires_at.is_not(None),
                    SlotReservation.expires_at <= now,
                )
                .values(status=ReservationStatus.EXPIRED)
                .returning(
                    SlotReservation.id,
                    SlotReservation.organization_id,
                    SlotReservation.branch_id,
                )
            )
            rows = result.all()
            for reservation_id, organization_id, branch_id in rows:
                append_audit_event(
                    session,
                    organization_id=organization_id,
                    action_code="booking.hold.expired",
                    actor=self._access.system_actor(
                        organization_id=organization_id,
                        task_id=f"hold-expiry:{reservation_id}",
                        operation="hold_expiry",
                        branch_ids=frozenset({branch_id}),
                    ),
                    branch_id=branch_id,
                    target_type="slot_reservation",
                    target_id=reservation_id,
                )
            return len(rows)

    async def _enqueue_due_daily_agendas(self, *, now: datetime) -> int:
        """Create one deduplicated agenda intent per specialist, branch, and local day."""

        inserted = 0
        async with self._database.session() as session, session.begin():
            settings_rows = (
                await session.execute(
                    sa.select(BookingSettings, BookingOrganization).join(
                        BookingOrganization,
                        BookingOrganization.id == BookingSettings.organization_id,
                    )
                )
            ).all()
            for settings, organization in settings_rows:
                bindings = (
                    await session.scalars(
                        sa.select(StaffTelegramBinding)
                        .where(
                            StaffTelegramBinding.organization_id == organization.id,
                            StaffTelegramBinding.membership_id.is_not(None),
                            StaffTelegramBinding.is_active.is_(True),
                            StaffTelegramBinding.telegram_chat_id.is_not(None),
                        )
                        .order_by(StaffTelegramBinding.id)
                    )
                ).all()
                for binding in bindings:
                    if binding.telegram_chat_id is None:
                        continue
                    branches = await self._agenda_branches(
                        session,
                        organization_id=organization.id,
                        specialist_id=binding.specialist_id,
                        now=now,
                    )
                    for branch in branches:
                        timezone = branch_timezone(
                            branch=branch,
                            organization=organization,
                        )
                        if timezone is None:
                            logger.warning(
                                "booking_worker_invalid_timezone",
                                extra={"organization_id": str(organization.id)},
                            )
                            continue
                        local_now = now.astimezone(timezone)
                        if (
                            local_now.timetz().replace(tzinfo=None)
                            < settings.daily_staff_agenda_time
                        ):
                            continue
                        local_day = local_now.date()
                        lower_bound, upper_bound = local_day_bounds(local_day, timezone)
                        appointments = (
                            await session.scalars(
                                sa.select(Appointment)
                                .where(
                                    Appointment.organization_id == organization.id,
                                    Appointment.branch_id == branch.id,
                                    Appointment.specialist_id == binding.specialist_id,
                                    Appointment.starts_at >= lower_bound,
                                    Appointment.starts_at < upper_bound,
                                    Appointment.status.in_(
                                        (
                                            AppointmentStatus.PENDING,
                                            AppointmentStatus.CONFIRMED,
                                        )
                                    ),
                                )
                                .order_by(Appointment.starts_at, Appointment.id)
                            )
                        ).all()
                        appointment_lines = "\n".join(
                            (
                                f"{appointment.starts_at.astimezone(timezone):%H:%M} — "
                                f"{appointment.service_name_snapshot}"
                            )
                            for appointment in appointments
                        )
                        template_key = (
                            "booking.daily_agenda.specialist"
                            if appointment_lines
                            else "booking.daily_agenda.empty"
                        )
                        statement = (
                            pg_insert(NotificationOutbox)
                            .values(
                                id=uuid4(),
                                organization_id=organization.id,
                                event_type="daily_staff_agenda",
                                channel="telegram",
                                recipient_type="specialist",
                                recipient_id=binding.specialist_id,
                                bot_app_id=binding.bot_app_id,
                                chat_id=binding.telegram_chat_id,
                                locale=settings.default_locale,
                                template_key=template_key,
                                payload={
                                    "appointments": appointment_lines,
                                    "branch_name": branch.name,
                                    "branch_id": str(branch.id),
                                },
                                scheduled_at=now,
                                status=OutboxStatus.PENDING,
                                attempts=0,
                                max_attempts=5,
                                dedupe_key=(
                                    "daily_staff_agenda:"
                                    f"{binding.id}:{branch.id}:{local_day.isoformat()}"
                                ),
                            )
                            .on_conflict_do_nothing(constraint="booking_notification_outbox_dedupe")
                            .returning(NotificationOutbox.id)
                        )
                        result = await session.execute(statement)
                        outbox_ids = result.scalars().all()
                        inserted += len(outbox_ids)
                        for outbox_id in outbox_ids:
                            append_audit_event(
                                session,
                                organization_id=organization.id,
                                action_code="worker.daily_agenda.enqueued",
                                actor=self._access.system_actor(
                                    organization_id=organization.id,
                                    task_id=f"daily-agenda:{outbox_id}",
                                    operation="daily_agenda",
                                    branch_ids=frozenset({branch.id}),
                                ),
                                branch_id=branch.id,
                                target_type="notification_outbox",
                                target_id=outbox_id,
                            )
        return inserted

    async def _agenda_branches(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        specialist_id: UUID,
        now: datetime,
    ) -> tuple[BookingBranch, ...]:
        """Find current work branches plus near-term appointment branches for a specialist."""

        assignment_rows = (
            await session.scalars(
                sa.select(BookingBranch)
                .join(SpecialistService, SpecialistService.branch_id == BookingBranch.id)
                .where(
                    BookingBranch.organization_id == organization_id,
                    BookingBranch.is_active.is_(True),
                    SpecialistService.organization_id == organization_id,
                    SpecialistService.specialist_id == specialist_id,
                    SpecialistService.is_active.is_(True),
                )
                .order_by(BookingBranch.name, BookingBranch.id)
            )
        ).all()
        schedule_rows = (
            await session.scalars(
                sa.select(BookingBranch)
                .join(WorkingSchedule, WorkingSchedule.branch_id == BookingBranch.id)
                .where(
                    BookingBranch.organization_id == organization_id,
                    BookingBranch.is_active.is_(True),
                    WorkingSchedule.organization_id == organization_id,
                    WorkingSchedule.specialist_id == specialist_id,
                    WorkingSchedule.is_active.is_(True),
                )
                .order_by(BookingBranch.name, BookingBranch.id)
            )
        ).all()
        appointment_rows = (
            await session.scalars(
                sa.select(BookingBranch)
                .join(Appointment, Appointment.branch_id == BookingBranch.id)
                .where(
                    BookingBranch.organization_id == organization_id,
                    Appointment.organization_id == organization_id,
                    Appointment.specialist_id == specialist_id,
                    Appointment.starts_at >= now - timedelta(days=2),
                    Appointment.starts_at < now + timedelta(days=2),
                    Appointment.status.in_(
                        (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
                    ),
                )
                .order_by(BookingBranch.name, BookingBranch.id)
            )
        ).all()
        branches = {branch.id: branch for branch in assignment_rows}
        branches.update({branch.id: branch for branch in schedule_rows})
        branches.update({branch.id: branch for branch in appointment_rows})
        return tuple(sorted(branches.values(), key=lambda branch: (branch.name, str(branch.id))))

    async def _claim_due(self, *, now: datetime) -> tuple[_OutboxWorkItem, ...]:
        """Lease a bounded batch with SKIP LOCKED before doing any external I/O."""

        stale_before = now - timedelta(seconds=self._lease_seconds)
        async with self._database.session() as session, session.begin():
            await session.execute(
                sa.update(NotificationOutbox)
                .where(
                    NotificationOutbox.status == OutboxStatus.PROCESSING,
                    NotificationOutbox.locked_at.is_not(None),
                    NotificationOutbox.locked_at < stale_before,
                    NotificationOutbox.attempts >= NotificationOutbox.max_attempts,
                )
                .values(
                    status=OutboxStatus.FAILED,
                    locked_at=None,
                    last_error="worker_lease_expired",
                )
            )
            await session.execute(
                sa.update(NotificationOutbox)
                .where(
                    NotificationOutbox.status == OutboxStatus.PROCESSING,
                    NotificationOutbox.locked_at.is_not(None),
                    NotificationOutbox.locked_at < stale_before,
                    NotificationOutbox.attempts < NotificationOutbox.max_attempts,
                )
                .values(
                    status=OutboxStatus.PENDING,
                    locked_at=None,
                    scheduled_at=now,
                    last_error="worker_lease_expired",
                )
            )
            rows = (
                await session.scalars(
                    sa.select(NotificationOutbox)
                    .where(
                        NotificationOutbox.status == OutboxStatus.PENDING,
                        NotificationOutbox.scheduled_at <= now,
                        NotificationOutbox.attempts < NotificationOutbox.max_attempts,
                    )
                    .order_by(
                        NotificationOutbox.scheduled_at,
                        NotificationOutbox.created_at,
                        NotificationOutbox.id,
                    )
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            claimed: list[_OutboxWorkItem] = []
            for row in rows:
                row.status = OutboxStatus.PROCESSING
                row.locked_at = now
                row.attempts += 1
                claimed.append(
                    _OutboxWorkItem(
                        id=row.id,
                        organization_id=row.organization_id,
                        appointment_id=row.appointment_id,
                        event_type=row.event_type,
                        recipient_type=row.recipient_type,
                        recipient_id=row.recipient_id,
                        bot_app_id=row.bot_app_id,
                        chat_id=row.chat_id,
                        locale=row.locale,
                        template_key=row.template_key,
                        payload=dict(row.payload),
                        scheduled_at=row.scheduled_at,
                        attempts=row.attempts,
                        max_attempts=row.max_attempts,
                    )
                )
            return tuple(claimed)

    async def _is_deliverable(self, *, work_item: _OutboxWorkItem, now: datetime) -> bool:
        """Recheck mutable recipient and appointment state immediately before delivery."""

        if work_item.chat_id is None or not work_item.bot_app_id:
            return False
        async with self._database.session() as session:
            appointment: Appointment | None = None
            target_branch_id = _payload_uuid(work_item.payload, "branch_id")
            if work_item.appointment_id is not None:
                appointment = await session.scalar(
                    sa.select(Appointment).where(
                        Appointment.id == work_item.appointment_id,
                        Appointment.organization_id == work_item.organization_id,
                    )
                )
                if appointment is None or not appointment_event_is_current(
                    event_type=work_item.event_type,
                    appointment=appointment,
                    payload=work_item.payload,
                    now=now,
                ):
                    return False
                target_branch_id = appointment.branch_id
            if work_item.recipient_type == "customer":
                if work_item.recipient_id is None:
                    return False
                customer = await session.scalar(
                    sa.select(Customer).where(
                        Customer.id == work_item.recipient_id,
                        Customer.organization_id == work_item.organization_id,
                    )
                )
                if customer is None or customer.is_blocked:
                    return False
                identity = await session.scalar(
                    sa.select(CustomerIdentity.id).where(
                        CustomerIdentity.organization_id == work_item.organization_id,
                        CustomerIdentity.customer_id == work_item.recipient_id,
                        CustomerIdentity.provider == "telegram",
                        CustomerIdentity.bot_app_id == work_item.bot_app_id,
                        CustomerIdentity.external_chat_id == work_item.chat_id,
                    )
                )
                if identity is None:
                    return False
            elif work_item.recipient_type in {"specialist", "inventory_manager"}:
                if work_item.recipient_id is None:
                    return False
                binding = await session.scalar(
                    sa.select(StaffTelegramBinding).where(
                        StaffTelegramBinding.organization_id == work_item.organization_id,
                        StaffTelegramBinding.specialist_id == work_item.recipient_id,
                        StaffTelegramBinding.bot_app_id == work_item.bot_app_id,
                        StaffTelegramBinding.telegram_chat_id == work_item.chat_id,
                        StaffTelegramBinding.is_active.is_(True),
                    )
                )
                if binding is None or binding.membership_id is None:
                    return False
                membership = await session.scalar(
                    sa.select(BookingMembership).where(
                        BookingMembership.id == binding.membership_id,
                        BookingMembership.organization_id == work_item.organization_id,
                        BookingMembership.is_active.is_(True),
                    )
                )
                if membership is None:
                    return False
                if (
                    work_item.recipient_type == "specialist"
                    and appointment is not None
                    and membership.specialist_id != appointment.specialist_id
                ):
                    return False
                required_permission = (
                    PermissionCode.BOOKINGS_VIEW
                    if work_item.recipient_type == "specialist"
                    else PermissionCode.INVENTORY_STOCK_VIEW
                )
                scope_rows = (
                    await session.execute(
                        sa.select(
                            BookingRoleAssignment.scope,
                            BookingRoleAssignmentBranch.branch_id,
                        )
                        .join(
                            BookingRolePermission,
                            BookingRolePermission.role_id == BookingRoleAssignment.role_id,
                        )
                        .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
                        .outerjoin(
                            BookingRoleAssignmentBranch,
                            BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
                        )
                        .where(
                            BookingRoleAssignment.organization_id == work_item.organization_id,
                            BookingRoleAssignment.membership_id == membership.id,
                            BookingRoleAssignment.is_active.is_(True),
                            BookingRole.is_active.is_(True),
                            BookingRolePermission.permission_code == required_permission.value,
                            sa.or_(
                                BookingRoleAssignment.starts_at.is_(None),
                                BookingRoleAssignment.starts_at <= now,
                            ),
                            sa.or_(
                                BookingRoleAssignment.ends_at.is_(None),
                                BookingRoleAssignment.ends_at > now,
                            ),
                        )
                    )
                ).all()
                if not scope_allows_notification(
                    scope_rows=[(scope, branch_id) for scope, branch_id in scope_rows],
                    target_branch_id=target_branch_id,
                    specialist_id=membership.specialist_id,
                    recipient_type=work_item.recipient_type,
                ):
                    return False
            return True

    async def _mark_sent(self, *, work_item_id: UUID, now: datetime) -> None:
        """Record a successful provider call after it has returned."""

        await self._update_claimed(
            work_item_id=work_item_id,
            values={
                "status": OutboxStatus.SENT,
                "sent_at": now,
                "locked_at": None,
                "last_error": None,
            },
        )

    async def _mark_cancelled(self, *, work_item_id: UUID) -> None:
        """Suppress an invalidated intent rather than retrying stale business state."""

        await self._update_claimed(
            work_item_id=work_item_id,
            values={"status": OutboxStatus.CANCELLED, "locked_at": None},
        )

    async def _mark_failed(self, *, work_item_id: UUID, reason: str) -> None:
        """Terminally fail a permanently rejected delivery without storing provider detail."""

        await self._update_claimed(
            work_item_id=work_item_id,
            values={"status": OutboxStatus.FAILED, "locked_at": None, "last_error": reason},
        )

    async def _retry_or_fail(self, *, work_item: _OutboxWorkItem, now: datetime) -> bool:
        """Use bounded exponential backoff for transient provider failures."""

        if work_item.attempts >= work_item.max_attempts:
            await self._mark_failed(work_item_id=work_item.id, reason="delivery_attempts_exhausted")
            return False
        delay_seconds = min(300, 2 ** min(work_item.attempts, 8))
        await self._update_claimed(
            work_item_id=work_item.id,
            values={
                "status": OutboxStatus.PENDING,
                "scheduled_at": now + timedelta(seconds=delay_seconds),
                "locked_at": None,
                "last_error": "transient_delivery_failure",
            },
        )
        return True

    async def _update_claimed(self, *, work_item_id: UUID, values: Mapping[str, object]) -> None:
        """Change only a work item still owned by this delivery attempt."""

        async with self._database.session() as session, session.begin():
            await session.execute(
                sa.update(NotificationOutbox)
                .where(
                    NotificationOutbox.id == work_item_id,
                    NotificationOutbox.status == OutboxStatus.PROCESSING,
                )
                .values(**values)
            )


def local_day_bounds(local_day: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    """Return UTC half-open boundaries for one calendar day in an IANA timezone."""

    starts_at = datetime.combine(local_day, time.min, tzinfo=timezone).astimezone(UTC)
    ends_at = datetime.combine(local_day + timedelta(days=1), time.min, tzinfo=timezone).astimezone(
        UTC
    )
    return starts_at, ends_at


def branch_timezone(
    *,
    branch: BookingBranch,
    organization: BookingOrganization,
) -> ZoneInfo | None:
    """Prefer the branch timezone and fall back only when it inherits the organization value."""

    try:
        return ZoneInfo(branch.timezone or organization.default_timezone)
    except ZoneInfoNotFoundError:
        return None


def appointment_event_is_current(
    *,
    event_type: str,
    appointment: Appointment,
    payload: Mapping[str, object],
    now: datetime,
) -> bool:
    """Avoid delivering a stale notification after a cancellation or reschedule race."""

    if event_type == "booking_reminder":
        expected_start = _payload_datetime(payload, "starts_at")
        return (
            appointment.status in {AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED}
            and appointment.starts_at > now
            and expected_start is not None
            and appointment.starts_at == expected_start
        )
    if event_type == "booking_cancelled":
        return appointment.status is AppointmentStatus.CANCELLED
    if event_type == "booking_completed":
        return appointment.status is AppointmentStatus.COMPLETED
    if event_type == "booking_confirmed":
        return appointment.status in {
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CHECKED_IN,
        }
    if event_type == "booking_rescheduled":
        expected_start = _payload_datetime(payload, "starts_at")
        return (
            appointment.status in _DELIVERABLE_APPOINTMENT_STATUSES
            and expected_start is not None
            and appointment.starts_at == expected_start
        )
    if event_type == "booking_created":
        return appointment.status in _DELIVERABLE_APPOINTMENT_STATUSES
    return True


def _payload_datetime(payload: Mapping[str, object], key: str) -> datetime | None:
    """Read an aware ISO timestamp from durable JSON without accepting malformed state."""

    value = payload.get(key)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return require_aware(parsed, field_name=key)
    except (TypeError, ValueError):
        return None


def _payload_uuid(payload: Mapping[str, object], key: str) -> UUID | None:
    """Read an optional UUID scope marker from durable outbox payload without trusting it."""

    value = payload.get(key)
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def scope_allows_notification(
    *,
    scope_rows: list[tuple[AccessScope, UUID | None]],
    target_branch_id: UUID | None,
    specialist_id: UUID | None,
    recipient_type: str,
) -> bool:
    """Use current role scope before sending delayed staff data through an external channel."""

    for scope, branch_id in scope_rows:
        if scope is AccessScope.ORGANIZATION:
            return True
        if (
            scope is AccessScope.SELF
            and recipient_type == "specialist"
            and specialist_id is not None
        ):
            return True
        if (
            scope is AccessScope.BRANCH
            and target_branch_id is not None
            and branch_id == target_branch_id
        ):
            return True
    return False
