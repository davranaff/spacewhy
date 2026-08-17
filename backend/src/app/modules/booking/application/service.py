"""Transactional booking use cases backed by PostgreSQL as the source of truth."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.booking.application.access import AccessPolicy
from app.modules.booking.application.audit import append_audit_event
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import (
    AppointmentResult,
    AvailabilityQuery,
    AvailabilityResult,
    CancelAppointmentCommand,
    CashShiftCommand,
    CashShiftResult,
    CashTransactionCommand,
    ConfirmAppointmentCommand,
    HoldCommand,
    HoldResult,
    PaymentCommand,
    PaymentResult,
    PriceOverrideCommand,
    RefundCommand,
    RescheduleCommitCommand,
    StatusTransitionCommand,
    StockMovementCommand,
    StockMovementResult,
)
from app.modules.booking.application.permissions import (
    BookingPermission,
    PermissionCode,
)
from app.modules.booking.domain.enums import (
    AccessRole,
    AccessScope,
    AppointmentStatus,
    CashShiftStatus,
    CashTransactionType,
    OutboxStatus,
    PaymentMethod,
    ReservationStatus,
    ReservationType,
    StockMovementType,
)
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.domain.slot_engine import (
    AvailabilityException as SlotAvailabilityException,
)
from app.modules.booking.domain.slot_engine import (
    SlotEngine,
    SlotPolicy,
    WeeklyWorkingInterval,
)
from app.modules.booking.domain.state_machine import require_transition
from app.modules.booking.domain.value_objects import TimeRange, require_aware
from app.modules.booking.infrastructure.persistence.models import (
    Appointment,
    AppointmentHistory,
    AppointmentMaterialSnapshot,
    AvailabilityException,
    BookingBranch,
    BookingIdempotencyRecord,
    BookingMembership,
    BookingOrganization,
    BookingRole,
    BookingRoleAssignment,
    BookingRoleAssignmentBranch,
    BookingRolePermission,
    BookingSettings,
    Cashbox,
    CashShift,
    CashTransaction,
    Customer,
    CustomerIdentity,
    NotificationOutbox,
    Payment,
    Product,
    Refund,
    ServiceMaterial,
    SlotReservation,
    Specialist,
    SpecialistService,
    StaffTelegramBinding,
    StockBalance,
    StockMovement,
    StockMovementItem,
    Warehouse,
    WorkingSchedule,
)
from app.modules.booking.infrastructure.persistence.models import (
    BookingService as BookingServiceModel,
)

_ACTIVE_APPOINTMENT_STATUSES = (
    AppointmentStatus.PENDING,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CHECKED_IN,
)


@dataclass(frozen=True, slots=True)
class _EffectiveSpecialistService:
    """Resolved specialist/service commercial inputs that callers cannot override."""

    specialist: Specialist
    assignment: SpecialistService
    duration_minutes: int
    price: Decimal
    buffer_before_minutes: int
    buffer_after_minutes: int


class BookingService:
    """Tenant-scoped use cases whose final conflict protection lives in PostgreSQL."""

    def __init__(
        self,
        *,
        database: Database,
        clock: Clock | None = None,
        slot_engine: SlotEngine | None = None,
        availability_max_days: int = 31,
    ) -> None:
        """Construct reusable application behavior with no FastAPI dependency."""

        if availability_max_days < 1:
            raise ValueError("availability_max_days must be positive.")
        self._database = database
        self._clock = clock or SystemClock()
        self._slot_engine = slot_engine or SlotEngine()
        self._availability_max_days = availability_max_days

    async def availability(
        self,
        *,
        actor: BookingActor,
        query: AvailabilityQuery,
    ) -> tuple[AvailabilityResult, ...]:
        """Calculate informational availability from one fully tenant-scoped data snapshot."""

        actor.require(BookingPermission.APPOINTMENTS_CREATE)
        if (
            query.customer_id is not None
            and actor.is_client
            and query.customer_id != actor.customer_id
        ):
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        if query.date_to < query.date_from:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        if (query.date_to - query.date_from).days > self._availability_max_days:
            raise BookingDomainError(BookingErrorCode.BOOKING_TOO_FAR_IN_FUTURE)
        async with self._database.session() as session:
            settings = await self._settings(session, actor.organization_id)
            branch = await self._branch(session, actor.organization_id, query.branch_id)
            if not actor.is_client:
                AccessPolicy.require_branch(
                    actor,
                    BookingPermission.APPOINTMENTS_CREATE,
                    branch.id,
                )
            service = await self._service(session, actor.organization_id, query.service_id)
            self._require_active_branch_service(branch=branch, service=service)
            timezone = self._timezone(
                branch, await self._organization(session, actor.organization_id)
            )
            now = require_aware(self._clock.now(), field_name="now")
            local_today = now.astimezone(timezone).date()
            max_day = local_today + timedelta(days=settings.max_booking_horizon_days)
            if query.date_from > max_day:
                raise BookingDomainError(BookingErrorCode.BOOKING_TOO_FAR_IN_FUTURE)
            candidate_rows = await self._specialist_assignments(
                session,
                organization_id=actor.organization_id,
                branch_id=query.branch_id,
                service=service,
                specialist_id=query.specialist_id,
            )
            if query.specialist_id is not None and not candidate_rows:
                await self._raise_specific_specialist_error(
                    session,
                    organization_id=actor.organization_id,
                    specialist_id=query.specialist_id,
                )
            return await self._availability_for_candidates(
                session,
                organization_id=actor.organization_id,
                branch=branch,
                settings=settings,
                candidates=candidate_rows,
                date_from=max(query.date_from, local_today),
                date_to=min(query.date_to, max_day),
                now=now,
                customer_id=query.customer_id or actor.customer_id,
            )

    async def client_bootstrap(self, *, actor: BookingActor) -> dict[str, Any]:
        """Return the bounded, server-derived configuration needed by a booking client."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        if actor.customer_id is None:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        async with self._database.session() as session:
            customer = await self._customer(session, actor.organization_id, actor.customer_id)
            settings = await self._settings(session, actor.organization_id)
            organization = await self._organization(session, actor.organization_id)
            branches = (
                await session.scalars(
                    sa.select(BookingBranch)
                    .where(
                        BookingBranch.organization_id == actor.organization_id,
                        BookingBranch.is_active.is_(True),
                    )
                    .order_by(BookingBranch.name, BookingBranch.id)
                )
            ).all()
            return {
                "customer": _customer_view(customer),
                "settings": {
                    "currency": settings.currency,
                    "default_locale": settings.default_locale,
                    "slot_step_minutes": settings.slot_step_minutes,
                    "require_client_phone": settings.require_client_phone,
                },
                "organization_timezone": organization.default_timezone,
                "available_locales": ["ru", "uz", "en"],
                "branches": [_branch_view(branch) for branch in branches],
                "feature_flags": {
                    "reschedule": True,
                    "client_cancellation": True,
                    "payments": False,
                },
            }

    async def list_branches(
        self,
        *,
        actor: BookingActor,
        active_only: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        """List tenant branches in a stable order without exposing archived tenant data."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            statement = sa.select(BookingBranch).where(
                BookingBranch.organization_id == actor.organization_id
            )
            if active_only:
                statement = statement.where(BookingBranch.is_active.is_(True))
            rows = (
                await session.scalars(statement.order_by(BookingBranch.name, BookingBranch.id))
            ).all()
            return tuple(_branch_view(branch) for branch in rows)

    async def list_categories(
        self,
        *,
        actor: BookingActor,
        active_only: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        """List service categories for public selection or authorized back-office use."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        from app.modules.booking.infrastructure.persistence.models import ServiceCategory

        async with self._database.session() as session:
            statement = sa.select(ServiceCategory).where(
                ServiceCategory.organization_id == actor.organization_id
            )
            if active_only:
                statement = statement.where(ServiceCategory.is_active.is_(True))
            rows = (
                await session.scalars(
                    statement.order_by(ServiceCategory.sort_order, ServiceCategory.name)
                )
            ).all()
            return tuple(_category_view(category) for category in rows)

    async def list_services(
        self,
        *,
        actor: BookingActor,
        branch_id: UUID | None = None,
        category_id: UUID | None = None,
        specialist_id: UUID | None = None,
        active_only: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        """List services filtered by actual branch/specialist eligibility when requested."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            statement = sa.select(BookingServiceModel).where(
                BookingServiceModel.organization_id == actor.organization_id
            )
            if category_id is not None:
                statement = statement.where(BookingServiceModel.category_id == category_id)
            if branch_id is not None or specialist_id is not None:
                statement = statement.join(
                    SpecialistService,
                    sa.and_(
                        SpecialistService.service_id == BookingServiceModel.id,
                        SpecialistService.organization_id == actor.organization_id,
                    ),
                )
                if branch_id is not None:
                    statement = statement.where(SpecialistService.branch_id == branch_id)
                if specialist_id is not None:
                    statement = statement.where(SpecialistService.specialist_id == specialist_id)
                if active_only:
                    statement = statement.where(
                        SpecialistService.is_active.is_(True),
                        SpecialistService.booking_enabled.is_(True),
                    )
                statement = statement.distinct()
            if active_only:
                statement = statement.where(
                    BookingServiceModel.is_active.is_(True),
                    BookingServiceModel.booking_enabled.is_(True),
                    BookingServiceModel.archived_at.is_(None),
                )
            rows = (
                await session.scalars(
                    statement.order_by(
                        BookingServiceModel.sort_order,
                        BookingServiceModel.name,
                        BookingServiceModel.id,
                    )
                )
            ).all()
            return tuple(_service_view(service) for service in rows)

    async def list_specialists(
        self,
        *,
        actor: BookingActor,
        branch_id: UUID | None = None,
        service_id: UUID | None = None,
        active_only: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        """List active specialists and restrict optional filters through their assignments."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            statement = sa.select(Specialist).where(
                Specialist.organization_id == actor.organization_id
            )
            if branch_id is not None or service_id is not None:
                statement = statement.join(
                    SpecialistService,
                    sa.and_(
                        SpecialistService.specialist_id == Specialist.id,
                        SpecialistService.organization_id == actor.organization_id,
                    ),
                )
                if branch_id is not None:
                    statement = statement.where(SpecialistService.branch_id == branch_id)
                if service_id is not None:
                    statement = statement.where(SpecialistService.service_id == service_id)
                if active_only:
                    statement = statement.where(
                        SpecialistService.is_active.is_(True),
                        SpecialistService.booking_enabled.is_(True),
                    )
                statement = statement.distinct()
            if active_only:
                statement = statement.where(
                    Specialist.is_active.is_(True),
                    Specialist.accepts_bookings.is_(True),
                    Specialist.archived_at.is_(None),
                )
            rows = (
                await session.scalars(statement.order_by(Specialist.display_name, Specialist.id))
            ).all()
            return tuple(_specialist_view(specialist) for specialist in rows)

    async def list_appointments(
        self,
        *,
        actor: BookingActor,
        upcoming: bool | None = None,
        history: bool | None = None,
        status: AppointmentStatus | None = None,
        branch_id: UUID | None = None,
        specialist_id: UUID | None = None,
        customer_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[AppointmentResult, ...]:
        """Return a bounded appointment list with read scope derived from the signed actor."""

        if limit < 1 or limit > 100 or offset < 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            statement = sa.select(Appointment).where(
                Appointment.organization_id == actor.organization_id,
                AccessPolicy.appointment_predicate(
                    actor,
                    BookingPermission.APPOINTMENTS_VIEW_OWN,
                ),
            )
            if customer_id is not None:
                statement = statement.where(Appointment.customer_id == customer_id)
            if specialist_id is not None:
                statement = statement.where(Appointment.specialist_id == specialist_id)
            if branch_id is not None:
                statement = statement.where(Appointment.branch_id == branch_id)
            if status is not None:
                statement = statement.where(Appointment.status == status)
            now = require_aware(self._clock.now(), field_name="now")
            if upcoming:
                statement = statement.where(
                    Appointment.starts_at >= now,
                    Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES),
                )
            if history:
                statement = statement.where(
                    sa.or_(
                        Appointment.starts_at < now,
                        Appointment.status.not_in(_ACTIVE_APPOINTMENT_STATUSES),
                    )
                )
            if date_from is not None:
                statement = statement.where(
                    Appointment.starts_at >= require_aware(date_from, field_name="date_from")
                )
            if date_to is not None:
                statement = statement.where(
                    Appointment.starts_at < require_aware(date_to, field_name="date_to")
                )
            rows = (
                await session.scalars(
                    statement.order_by(Appointment.starts_at, Appointment.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
            return await self._appointment_results(session, rows)

    async def get_appointment(
        self,
        *,
        actor: BookingActor,
        appointment_id: UUID,
    ) -> AppointmentResult:
        """Load one appointment only when the actor's derived read scope includes it."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            appointment = await self._appointment(
                session,
                organization_id=actor.organization_id,
                appointment_id=appointment_id,
                for_update=False,
            )
            self._require_appointment_read_access(actor=actor, appointment=appointment)
            return await self._appointment_result(session, appointment)

    async def staff_agenda(
        self,
        *,
        actor: BookingActor,
        local_day: date,
        branch_id: UUID | None = None,
    ) -> tuple[AppointmentResult, ...]:
        """Return only the actor's scoped agenda for one local day."""

        actor.require(BookingPermission.APPOINTMENTS_VIEW_OWN)
        async with self._database.session() as session:
            organization = await self._organization(session, actor.organization_id)
            timezone = ZoneInfo(organization.default_timezone)
            lower = datetime.combine(local_day, datetime.min.time(), tzinfo=timezone).astimezone(
                UTC
            )
            upper = datetime.combine(
                local_day + timedelta(days=1), datetime.min.time(), tzinfo=timezone
            ).astimezone(UTC)
            statement = sa.select(Appointment).where(
                Appointment.organization_id == actor.organization_id,
                Appointment.starts_at >= lower,
                Appointment.starts_at < upper,
                AccessPolicy.appointment_predicate(
                    actor,
                    BookingPermission.APPOINTMENTS_VIEW_OWN,
                ),
            )
            if branch_id is not None:
                statement = statement.where(Appointment.branch_id == branch_id)
            rows = (
                await session.scalars(statement.order_by(Appointment.starts_at, Appointment.id))
            ).all()
            return await self._appointment_results(session, rows)

    async def create_hold(
        self,
        *,
        actor: BookingActor,
        command: HoldCommand,
    ) -> HoldResult:
        """Create a DB-backed active hold after a final transactional slot calculation."""

        actor.require(BookingPermission.APPOINTMENTS_CREATE)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        requested_start = require_aware(command.starts_at, field_name="starts_at")
        request_hash = _request_hash(
            {
                "branch_id": str(command.branch_id),
                "service_id": str(command.service_id),
                "specialist_id": str(command.specialist_id) if command.specialist_id else None,
                "starts_at": requested_start.isoformat(),
                "customer_id": str(command.customer_id or actor.customer_id)
                if command.customer_id or actor.customer_id
                else None,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="hold.create",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="hold.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _hold_from_payload(replay)
                result = await self._create_hold_in_transaction(
                    session,
                    actor=actor,
                    command=command,
                    requested_start=requested_start,
                    enforce_upcoming_limit=True,
                )
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="hold.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_hold_payload(result),
                )
            return result

    async def create_reschedule_hold(
        self,
        *,
        actor: BookingActor,
        appointment_id: UUID,
        command: HoldCommand,
    ) -> HoldResult:
        """Create a new hold while leaving the current appointment reservation intact."""

        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        requested_start = require_aware(command.starts_at, field_name="starts_at")
        request_hash = _request_hash(
            {
                "appointment_id": str(appointment_id),
                "branch_id": str(command.branch_id),
                "service_id": str(command.service_id),
                "specialist_id": str(command.specialist_id) if command.specialist_id else None,
                "starts_at": requested_start.isoformat(),
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=appointment_id,
                    for_update=True,
                )
                await self._require_reschedule_access(
                    session,
                    actor=actor,
                    appointment=appointment,
                    now=require_aware(self._clock.now(), field_name="now"),
                )
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_hold",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_hold",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _hold_from_payload(replay)
                if (
                    command.branch_id != appointment.branch_id
                    or command.service_id != appointment.service_id
                    or (
                        command.customer_id is not None
                        and command.customer_id != appointment.customer_id
                    )
                ):
                    raise BookingDomainError(BookingErrorCode.RESCHEDULE_NOT_ALLOWED)
                reschedule_command = HoldCommand(
                    branch_id=command.branch_id,
                    service_id=command.service_id,
                    specialist_id=command.specialist_id,
                    starts_at=command.starts_at,
                    idempotency_key=command.idempotency_key,
                    customer_id=appointment.customer_id,
                )
                result = await self._create_hold_in_transaction(
                    session,
                    actor=actor,
                    command=reschedule_command,
                    requested_start=requested_start,
                    enforce_upcoming_limit=False,
                    excluded_customer_reservation_id=appointment.reservation_id,
                    required_permission=BookingPermission.APPOINTMENTS_RESCHEDULE,
                )
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_hold",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_hold_payload(result),
                )
            return result

    async def confirm_appointment(
        self,
        *,
        actor: BookingActor,
        command: ConfirmAppointmentCommand,
    ) -> AppointmentResult:
        """Promote an owned active hold into one immutable appointment and outbox intent."""

        actor.require(BookingPermission.APPOINTMENTS_CREATE)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "hold_id": str(command.hold_id),
                "customer_note": command.customer_note,
                "source": command.source.value,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="appointment.confirm",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="appointment.confirm",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _appointment_from_payload(replay)
                now = require_aware(self._clock.now(), field_name="now")
                hold = await session.scalar(
                    sa.select(SlotReservation)
                    .where(
                        SlotReservation.id == command.hold_id,
                        SlotReservation.organization_id == actor.organization_id,
                    )
                    .with_for_update()
                )
                if hold is None or hold.type is not ReservationType.HOLD:
                    raise BookingDomainError(BookingErrorCode.HOLD_NOT_FOUND)
                self._require_hold_owner(actor=actor, hold=hold)
                if hold.status is not ReservationStatus.ACTIVE:
                    raise BookingDomainError(BookingErrorCode.HOLD_EXPIRED)
                if hold.expires_at is None or hold.expires_at <= now:
                    hold.status = ReservationStatus.EXPIRED
                    raise BookingDomainError(BookingErrorCode.HOLD_EXPIRED)
                if hold.customer_id is None:
                    raise BookingDomainError(BookingErrorCode.HOLD_OWNER_MISMATCH)
                customer = await self._customer(session, actor.organization_id, hold.customer_id)
                if customer.is_blocked:
                    raise BookingDomainError(BookingErrorCode.CUSTOMER_BLOCKED)
                settings = await self._settings(session, actor.organization_id)
                branch = await self._branch(session, actor.organization_id, hold.branch_id)
                service = await self._service(session, actor.organization_id, hold.service_id)
                self._require_active_branch_service(branch=branch, service=service)
                candidates = await self._specialist_assignments(
                    session,
                    organization_id=actor.organization_id,
                    branch_id=branch.id,
                    service=service,
                    specialist_id=hold.specialist_id,
                    for_update=True,
                )
                if not candidates:
                    await self._raise_specific_specialist_error(
                        session,
                        organization_id=actor.organization_id,
                        specialist_id=hold.specialist_id,
                    )
                candidate = candidates[0]
                appointment_id = uuid4()
                status = (
                    AppointmentStatus.CONFIRMED
                    if settings.auto_confirm_booking
                    else AppointmentStatus.PENDING
                )
                appointment = Appointment(
                    id=appointment_id,
                    public_number=_public_appointment_number(appointment_id, now),
                    organization_id=actor.organization_id,
                    branch_id=branch.id,
                    customer_id=customer.id,
                    specialist_id=candidate.specialist.id,
                    service_id=service.id,
                    reservation_id=hold.id,
                    status=status,
                    source=command.source,
                    starts_at=hold.starts_at,
                    ends_at=hold.ends_at,
                    busy_starts_at=hold.busy_starts_at,
                    busy_ends_at=hold.busy_ends_at,
                    service_name_snapshot=service.name,
                    specialist_name_snapshot=candidate.specialist.display_name,
                    duration_minutes_snapshot=_duration_minutes(hold.starts_at, hold.ends_at),
                    price_snapshot=candidate.price,
                    currency_snapshot=service.currency,
                    customer_note=_optional_limited_text(command.customer_note, 5_000),
                    created_by=actor.subject_id,
                    confirmed_at=now if status is AppointmentStatus.CONFIRMED else None,
                )
                session.add(appointment)
                await session.flush()
                hold.type = ReservationType.APPOINTMENT
                hold.expires_at = None
                hold.appointment_id = appointment.id
                await self._snapshot_service_materials(
                    session,
                    organization_id=actor.organization_id,
                    appointment=appointment,
                )
                session.add(
                    AppointmentHistory(
                        organization_id=actor.organization_id,
                        appointment_id=appointment.id,
                        event_type="created",
                        old_status=None,
                        new_status=status,
                        actor_type=actor.actor_type,
                        actor_id=actor.subject_id,
                        metadata_json={"source": command.source.value},
                    )
                )
                await self._schedule_appointment_notifications(
                    session,
                    organization_id=actor.organization_id,
                    appointment=appointment,
                    customer=customer,
                    settings=settings,
                    now=now,
                    event_type=(
                        "booking_confirmed"
                        if status is AppointmentStatus.CONFIRMED
                        else "booking_created"
                    ),
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="appointment.created",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="appointment",
                    target_id=appointment.id,
                    after={
                        "status": appointment.status.value,
                        "starts_at": appointment.starts_at.isoformat(),
                        "service_id": str(appointment.service_id),
                        "specialist_id": str(appointment.specialist_id),
                    },
                    metadata={"source": command.source.value},
                )
                result = await self._appointment_result(session, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="appointment.confirm",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_appointment_payload(result),
                )
            return result

    async def cancel_appointment(
        self,
        *,
        actor: BookingActor,
        command: CancelAppointmentCommand,
    ) -> AppointmentResult:
        """Cancel an appointment, release its busy reservation, and cancel future reminders."""

        actor.require(BookingPermission.APPOINTMENTS_CANCEL)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "appointment_id": str(command.appointment_id),
                "reason": command.reason,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="appointment.cancel",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="appointment.cancel",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _appointment_from_payload(replay)
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=command.appointment_id,
                    for_update=True,
                )
                now = require_aware(self._clock.now(), field_name="now")
                await self._require_cancellation_access(
                    session,
                    actor=actor,
                    appointment=appointment,
                    now=now,
                    reason=command.reason,
                )
                old_status = appointment.status
                await self._cancel_appointment_in_transaction(
                    session,
                    actor=actor,
                    appointment=appointment,
                    now=now,
                    reason=command.reason,
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="appointment.cancelled",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="appointment",
                    target_id=appointment.id,
                    reason=command.reason,
                    before={"status": old_status.value},
                    after={"status": appointment.status.value},
                )
                result = await self._appointment_result(session, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="appointment.cancel",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_appointment_payload(result),
                )
            return result

    async def commit_reschedule(
        self,
        *,
        actor: BookingActor,
        command: RescheduleCommitCommand,
    ) -> AppointmentResult:
        """Atomically replace a live appointment reservation with a verified new hold."""

        actor.require(BookingPermission.APPOINTMENTS_RESCHEDULE)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "appointment_id": str(command.appointment_id),
                "hold_id": str(command.hold_id),
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_commit",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_commit",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _appointment_from_payload(replay)
                now = require_aware(self._clock.now(), field_name="now")
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=command.appointment_id,
                    for_update=True,
                )
                await self._require_reschedule_access(
                    session,
                    actor=actor,
                    appointment=appointment,
                    now=now,
                )
                old_reservation = await self._reservation(
                    session,
                    organization_id=actor.organization_id,
                    reservation_id=appointment.reservation_id,
                    for_update=True,
                )
                new_hold = await self._reservation(
                    session,
                    organization_id=actor.organization_id,
                    reservation_id=command.hold_id,
                    for_update=True,
                    missing_code=BookingErrorCode.HOLD_NOT_FOUND,
                )
                self._require_hold_owner(
                    actor=actor,
                    hold=new_hold,
                    permission=BookingPermission.APPOINTMENTS_RESCHEDULE,
                )
                if (
                    new_hold.type is not ReservationType.HOLD
                    or new_hold.status is not ReservationStatus.ACTIVE
                    or new_hold.expires_at is None
                    or new_hold.expires_at <= now
                ):
                    if new_hold.type is ReservationType.HOLD and new_hold.expires_at is not None:
                        new_hold.status = ReservationStatus.EXPIRED
                    raise BookingDomainError(BookingErrorCode.HOLD_EXPIRED)
                if (
                    new_hold.customer_id != appointment.customer_id
                    or new_hold.branch_id != appointment.branch_id
                    or new_hold.service_id != appointment.service_id
                ):
                    raise BookingDomainError(BookingErrorCode.RESCHEDULE_NOT_ALLOWED)
                service = await self._service(
                    session, actor.organization_id, appointment.service_id
                )
                candidates = await self._specialist_assignments(
                    session,
                    organization_id=actor.organization_id,
                    branch_id=appointment.branch_id,
                    service=service,
                    specialist_id=new_hold.specialist_id,
                    for_update=True,
                )
                if not candidates:
                    raise BookingDomainError(BookingErrorCode.SPECIALIST_UNAVAILABLE)
                candidate = candidates[0]
                old_starts_at = appointment.starts_at
                old_status = appointment.status
                old_reservation.status = ReservationStatus.RELEASED
                old_reservation.appointment_id = None
                new_hold.type = ReservationType.APPOINTMENT
                new_hold.expires_at = None
                new_hold.appointment_id = appointment.id
                appointment.reservation_id = new_hold.id
                appointment.specialist_id = new_hold.specialist_id
                appointment.starts_at = new_hold.starts_at
                appointment.ends_at = new_hold.ends_at
                appointment.busy_starts_at = new_hold.busy_starts_at
                appointment.busy_ends_at = new_hold.busy_ends_at
                appointment.specialist_name_snapshot = candidate.specialist.display_name
                appointment.duration_minutes_snapshot = _duration_minutes(
                    new_hold.starts_at,
                    new_hold.ends_at,
                )
                appointment.price_snapshot = candidate.price
                appointment.version += 1
                session.add(
                    AppointmentHistory(
                        organization_id=actor.organization_id,
                        appointment_id=appointment.id,
                        event_type="rescheduled",
                        old_status=old_status,
                        new_status=old_status,
                        old_starts_at=old_starts_at,
                        new_starts_at=new_hold.starts_at,
                        actor_type=actor.actor_type,
                        actor_id=actor.subject_id,
                        metadata_json={"old_reservation_id": str(old_reservation.id)},
                    )
                )
                await self._cancel_future_reminders(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=appointment.id,
                )
                settings = await self._settings(session, actor.organization_id)
                customer = await self._customer(
                    session, actor.organization_id, appointment.customer_id
                )
                await self._schedule_appointment_notifications(
                    session,
                    organization_id=actor.organization_id,
                    appointment=appointment,
                    customer=customer,
                    settings=settings,
                    now=now,
                    event_type="booking_rescheduled",
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="appointment.rescheduled",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="appointment",
                    target_id=appointment.id,
                    before={"starts_at": old_starts_at.isoformat()},
                    after={
                        "starts_at": appointment.starts_at.isoformat(),
                        "specialist_id": str(appointment.specialist_id),
                    },
                )
                result = await self._appointment_result(session, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="appointment.reschedule_commit",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_appointment_payload(result),
                )
            return result

    async def transition_appointment(
        self,
        *,
        actor: BookingActor,
        command: StatusTransitionCommand,
    ) -> AppointmentResult:
        """Apply a permitted staff/admin appointment transition under a row lock."""

        transition_permission = self._require_transition_permission(actor, command.target_status)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "appointment_id": str(command.appointment_id),
                "target_status": command.target_status.value,
                "reason": command.reason,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation=f"appointment.transition.{command.target_status.value}",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation=f"appointment.transition.{command.target_status.value}",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _appointment_from_payload(replay)
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=command.appointment_id,
                    for_update=True,
                )
                await self._require_staff_appointment_access(
                    actor=actor,
                    appointment=appointment,
                    permission=transition_permission,
                )
                now = require_aware(self._clock.now(), field_name="now")
                status_before = appointment.status
                if command.target_status is AppointmentStatus.CANCELLED:
                    await self._require_cancellation_access(
                        session,
                        actor=actor,
                        appointment=appointment,
                        now=now,
                        reason=command.reason,
                    )
                    await self._cancel_appointment_in_transaction(
                        session,
                        actor=actor,
                        appointment=appointment,
                        now=now,
                        reason=command.reason,
                    )
                elif command.target_status is AppointmentStatus.COMPLETED:
                    await self._complete_appointment_in_transaction(
                        session,
                        actor=actor,
                        appointment=appointment,
                        now=now,
                    )
                else:
                    require_transition(appointment.status, command.target_status)
                    old_status = appointment.status
                    appointment.status = command.target_status
                    appointment.version += 1
                    _apply_transition_timestamp(
                        appointment=appointment,
                        target_status=command.target_status,
                        now=now,
                    )
                    if command.target_status is AppointmentStatus.NO_SHOW:
                        reservation = await self._reservation(
                            session,
                            organization_id=actor.organization_id,
                            reservation_id=appointment.reservation_id,
                            for_update=True,
                        )
                        reservation.status = ReservationStatus.RELEASED
                        await self._cancel_future_reminders(
                            session,
                            organization_id=actor.organization_id,
                            appointment_id=appointment.id,
                        )
                    session.add(
                        AppointmentHistory(
                            organization_id=actor.organization_id,
                            appointment_id=appointment.id,
                            event_type=command.target_status.value,
                            old_status=old_status,
                            new_status=command.target_status,
                            actor_type=actor.actor_type,
                            actor_id=actor.subject_id,
                            reason=_optional_limited_text(command.reason, 500),
                            metadata_json={},
                        )
                    )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="appointment.status_changed",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="appointment",
                    target_id=appointment.id,
                    reason=command.reason,
                    before={"status": status_before.value},
                    after={"status": appointment.status.value},
                    metadata={"target_status": command.target_status.value},
                )
                result = await self._appointment_result(session, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation=f"appointment.transition.{command.target_status.value}",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_appointment_payload(result),
                )
            return result

    async def override_appointment_price(
        self,
        *,
        actor: BookingActor,
        command: PriceOverrideCommand,
    ) -> AppointmentResult:
        """Change a snapshot only with a reason, durable replay key, and audit evidence."""

        actor.require(BookingPermission.APPOINTMENTS_OVERRIDE_RULES)
        if command.price < Decimal("0") or not _optional_limited_text(command.reason, 500):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        if not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "appointment_id": str(command.appointment_id),
                "price": str(command.price),
                "reason": command.reason,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="appointment.price_override",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="appointment.price_override",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _appointment_from_payload(replay)
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=command.appointment_id,
                    for_update=True,
                )
                await self._require_staff_appointment_access(
                    actor=actor,
                    appointment=appointment,
                    permission=BookingPermission.APPOINTMENTS_OVERRIDE_RULES,
                )
                old_price = appointment.price_snapshot
                appointment.price_snapshot = command.price
                appointment.version += 1
                now = require_aware(self._clock.now(), field_name="now")
                reason = _optional_limited_text(command.reason, 500)
                session.add(
                    AppointmentHistory(
                        organization_id=actor.organization_id,
                        appointment_id=appointment.id,
                        event_type="price_overridden",
                        old_status=appointment.status,
                        new_status=appointment.status,
                        actor_type=actor.actor_type,
                        actor_id=actor.subject_id,
                        reason=reason,
                        metadata_json={
                            "old_price": str(old_price),
                            "new_price": str(command.price),
                            "currency": appointment.currency_snapshot,
                        },
                    )
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="appointment.price_overridden",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="appointment",
                    target_id=appointment.id,
                    reason=reason,
                    before={"price": str(old_price)},
                    after={"price": str(command.price)},
                    metadata={"currency": appointment.currency_snapshot, "at": now.isoformat()},
                )
                result = await self._appointment_result(session, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="appointment.price_override",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_appointment_payload(result),
                )
            return result

    async def open_cash_shift(
        self,
        *,
        actor: BookingActor,
        command: CashShiftCommand,
    ) -> CashShiftResult:
        """Open exactly one shift per cashbox and write its immutable opening ledger row."""

        actor.require(PermissionCode.CASH_SHIFTS_OPEN)
        if command.amount < Decimal("0") or not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "cashbox_id": str(command.cashbox_id),
                "amount": str(command.amount),
                "notes": command.notes,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="cash_shift.open",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="cash_shift.open",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _cash_shift_from_payload(replay)
                cashbox = await self._cashbox(
                    session,
                    organization_id=actor.organization_id,
                    cashbox_id=command.cashbox_id,
                )
                AccessPolicy.require_branch(
                    actor, PermissionCode.CASH_SHIFTS_OPEN, cashbox.branch_id
                )
                await self._cashbox_lock(session, cashbox.id)
                existing = await session.scalar(
                    sa.select(CashShift)
                    .where(
                        CashShift.organization_id == actor.organization_id,
                        CashShift.cashbox_id == cashbox.id,
                        CashShift.status == CashShiftStatus.OPEN,
                    )
                    .with_for_update()
                )
                if existing is not None:
                    raise BookingDomainError(BookingErrorCode.CASH_SHIFT_ALREADY_OPEN)
                now = require_aware(self._clock.now(), field_name="now")
                shift = CashShift(
                    organization_id=actor.organization_id,
                    cashbox_id=cashbox.id,
                    opened_by=actor.subject_id,
                    opened_at=now,
                    opening_amount=command.amount,
                    status=CashShiftStatus.OPEN,
                    notes=_optional_limited_text(command.notes, 500),
                )
                session.add(shift)
                await session.flush()
                session.add(
                    CashTransaction(
                        organization_id=actor.organization_id,
                        cashbox_id=cashbox.id,
                        cash_shift_id=shift.id,
                        type=CashTransactionType.SHIFT_OPENING,
                        amount_delta=command.amount,
                        currency=cashbox.currency,
                        reference_type="cash_shift",
                        reference_id=shift.id,
                        created_by=actor.subject_id,
                        idempotency_key=f"cash_shift_open:{shift.id}",
                    )
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="cash.shift.opened",
                    actor=actor,
                    branch_id=cashbox.branch_id,
                    target_type="cash_shift",
                    target_id=shift.id,
                    after={"opening_amount": str(shift.opening_amount)},
                    metadata={"cashbox_id": str(cashbox.id), "currency": cashbox.currency},
                )
                result = _cash_shift_result(shift)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="cash_shift.open",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_cash_shift_payload(result),
                )
            return result

    async def close_cash_shift(
        self,
        *,
        actor: BookingActor,
        command: CashShiftCommand,
    ) -> CashShiftResult:
        """Close a cashbox's live shift after serializing payment/refund ledger writes."""

        actor.require(PermissionCode.CASH_SHIFTS_CLOSE)
        if command.amount < Decimal("0") or not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "cashbox_id": str(command.cashbox_id),
                "amount": str(command.amount),
                "notes": command.notes,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="cash_shift.close",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="cash_shift.close",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _cash_shift_from_payload(replay)
                cashbox = await self._cashbox(
                    session,
                    organization_id=actor.organization_id,
                    cashbox_id=command.cashbox_id,
                )
                AccessPolicy.require_branch(
                    actor, PermissionCode.CASH_SHIFTS_CLOSE, cashbox.branch_id
                )
                await self._cashbox_lock(session, cashbox.id)
                shift = await session.scalar(
                    sa.select(CashShift)
                    .where(
                        CashShift.organization_id == actor.organization_id,
                        CashShift.cashbox_id == cashbox.id,
                        CashShift.status == CashShiftStatus.OPEN,
                    )
                    .with_for_update()
                )
                if shift is None:
                    raise BookingDomainError(BookingErrorCode.CASH_SHIFT_NOT_OPEN)
                if shift.opened_by != actor.subject_id:
                    AccessPolicy.require_branch(
                        actor,
                        PermissionCode.CASH_SHIFTS_MANAGE_OTHERS,
                        cashbox.branch_id,
                    )
                expected = _decimal_or_zero(
                    await session.scalar(
                        sa.select(
                            sa.func.coalesce(sa.func.sum(CashTransaction.amount_delta), 0)
                        ).where(
                            CashTransaction.organization_id == actor.organization_id,
                            CashTransaction.cash_shift_id == shift.id,
                        )
                    )
                )
                now = require_aware(self._clock.now(), field_name="now")
                shift.status = CashShiftStatus.CLOSED
                shift.closed_by = actor.subject_id
                shift.closed_at = now
                shift.expected_closing_amount = expected
                shift.actual_closing_amount = command.amount
                shift.difference = command.amount - expected
                shift.notes = _optional_limited_text(command.notes, 500) or shift.notes
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="cash.shift.closed",
                    actor=actor,
                    branch_id=cashbox.branch_id,
                    target_type="cash_shift",
                    target_id=shift.id,
                    before={"status": CashShiftStatus.OPEN.value},
                    after={
                        "status": shift.status.value,
                        "expected_closing_amount": str(expected),
                        "actual_closing_amount": str(command.amount),
                        "difference": str(shift.difference),
                    },
                    metadata={"cashbox_id": str(cashbox.id), "currency": cashbox.currency},
                )
                result = _cash_shift_result(shift)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="cash_shift.close",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_cash_shift_payload(result),
                )
            return result

    async def record_payment(
        self,
        *,
        actor: BookingActor,
        command: PaymentCommand,
    ) -> PaymentResult:
        """Record a bounded payment and optional cash ledger entry in one transaction."""

        actor.require(PermissionCode.CASH_PAYMENTS_CREATE)
        if command.amount <= Decimal("0") or not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "appointment_id": str(command.appointment_id),
                "amount": str(command.amount),
                "currency": command.currency,
                "method": command.method.value,
                "cashbox_id": str(command.cashbox_id) if command.cashbox_id else None,
                "external_reference": command.external_reference,
                "note": command.note,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="payment.create",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="payment.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _payment_from_payload(replay)
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=command.appointment_id,
                    for_update=True,
                )
                AccessPolicy.require_appointment(
                    actor,
                    PermissionCode.CASH_PAYMENTS_CREATE,
                    branch_id=appointment.branch_id,
                    specialist_id=appointment.specialist_id,
                    customer_id=appointment.customer_id,
                )
                if appointment.currency_snapshot != command.currency:
                    raise BookingDomainError(BookingErrorCode.CURRENCY_MISMATCH)
                paid_before = _decimal_or_zero(
                    await session.scalar(
                        sa.select(sa.func.coalesce(sa.func.sum(Payment.amount), 0)).where(
                            Payment.organization_id == actor.organization_id,
                            Payment.appointment_id == appointment.id,
                        )
                    )
                )
                if paid_before + command.amount > appointment.price_snapshot:
                    raise BookingDomainError(BookingErrorCode.PAYMENT_EXCEEDS_OUTSTANDING_AMOUNT)
                cashbox: Cashbox | None = None
                cash_shift: CashShift | None = None
                if command.method is PaymentMethod.CASH:
                    cashbox, cash_shift = await self._cash_payment_shift(
                        session,
                        organization_id=actor.organization_id,
                        cashbox_id=command.cashbox_id,
                        currency=command.currency,
                    )
                    if cashbox.branch_id != appointment.branch_id:
                        raise BookingDomainError(BookingErrorCode.FORBIDDEN)
                    AccessPolicy.require_branch(
                        actor,
                        PermissionCode.CASH_PAYMENTS_CREATE,
                        cashbox.branch_id,
                    )
                payment = Payment(
                    organization_id=actor.organization_id,
                    appointment_id=appointment.id,
                    amount=command.amount,
                    currency=command.currency,
                    method=command.method,
                    cash_shift_id=cash_shift.id if cash_shift is not None else None,
                    created_by=actor.subject_id,
                    idempotency_key=command.idempotency_key,
                    external_reference=_optional_limited_text(command.external_reference, 200),
                    note=_optional_limited_text(command.note, 500),
                )
                session.add(payment)
                await session.flush()
                if cashbox is not None and cash_shift is not None:
                    session.add(
                        CashTransaction(
                            organization_id=actor.organization_id,
                            cashbox_id=cashbox.id,
                            cash_shift_id=cash_shift.id,
                            type=CashTransactionType.APPOINTMENT_PAYMENT,
                            amount_delta=command.amount,
                            currency=command.currency,
                            reference_type="payment",
                            reference_id=payment.id,
                            created_by=actor.subject_id,
                            idempotency_key=f"payment:{payment.id}",
                        )
                    )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="cash.payment.created",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="payment",
                    target_id=payment.id,
                    after={
                        "appointment_id": str(appointment.id),
                        "amount": str(payment.amount),
                        "method": payment.method.value,
                    },
                    metadata={
                        "currency": payment.currency,
                        "cashbox_id": str(cashbox.id) if cashbox else None,
                    },
                )
                result = await self._payment_result(session, payment, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="payment.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_payment_payload(result),
                )
            return result

    async def refund_payment(
        self,
        *,
        actor: BookingActor,
        command: RefundCommand,
    ) -> PaymentResult:
        """Create an immutable refund after locking the original payment and any cash shift."""

        actor.require(PermissionCode.CASH_REFUNDS_CREATE)
        if command.amount <= Decimal("0") or not command.reason or not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "payment_id": str(command.payment_id),
                "amount": str(command.amount),
                "currency": command.currency,
                "cashbox_id": str(command.cashbox_id) if command.cashbox_id else None,
                "reason": command.reason,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="refund.create",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="refund.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _payment_from_payload(replay)
                payment = await session.scalar(
                    sa.select(Payment)
                    .where(
                        Payment.id == command.payment_id,
                        Payment.organization_id == actor.organization_id,
                    )
                    .with_for_update()
                )
                if payment is None:
                    raise BookingDomainError(BookingErrorCode.APPOINTMENT_NOT_FOUND)
                appointment = await self._appointment(
                    session,
                    organization_id=actor.organization_id,
                    appointment_id=payment.appointment_id,
                    for_update=True,
                )
                AccessPolicy.require_appointment(
                    actor,
                    PermissionCode.CASH_REFUNDS_CREATE,
                    branch_id=appointment.branch_id,
                    specialist_id=appointment.specialist_id,
                    customer_id=appointment.customer_id,
                )
                if payment.currency != command.currency:
                    raise BookingDomainError(BookingErrorCode.CURRENCY_MISMATCH)
                refunded_before = _decimal_or_zero(
                    await session.scalar(
                        sa.select(sa.func.coalesce(sa.func.sum(Refund.amount), 0)).where(
                            Refund.organization_id == actor.organization_id,
                            Refund.payment_id == payment.id,
                        )
                    )
                )
                if refunded_before + command.amount > payment.amount:
                    raise BookingDomainError(BookingErrorCode.REFUND_EXCEEDS_REFUNDABLE_AMOUNT)
                cashbox: Cashbox | None = None
                cash_shift: CashShift | None = None
                if payment.method is PaymentMethod.CASH:
                    cashbox, cash_shift = await self._cash_payment_shift(
                        session,
                        organization_id=actor.organization_id,
                        cashbox_id=command.cashbox_id,
                        currency=command.currency,
                    )
                    if cashbox.branch_id != appointment.branch_id:
                        raise BookingDomainError(BookingErrorCode.FORBIDDEN)
                    AccessPolicy.require_branch(
                        actor,
                        PermissionCode.CASH_REFUNDS_CREATE,
                        cashbox.branch_id,
                    )
                refund = Refund(
                    organization_id=actor.organization_id,
                    payment_id=payment.id,
                    amount=command.amount,
                    currency=command.currency,
                    cash_shift_id=cash_shift.id if cash_shift is not None else None,
                    reason=_optional_limited_text(command.reason, 500) or "refund",
                    created_by=actor.subject_id,
                    idempotency_key=command.idempotency_key,
                )
                session.add(refund)
                await session.flush()
                if cashbox is not None and cash_shift is not None:
                    session.add(
                        CashTransaction(
                            organization_id=actor.organization_id,
                            cashbox_id=cashbox.id,
                            cash_shift_id=cash_shift.id,
                            type=CashTransactionType.REFUND,
                            amount_delta=-command.amount,
                            currency=command.currency,
                            reference_type="refund",
                            reference_id=refund.id,
                            created_by=actor.subject_id,
                            idempotency_key=f"refund:{refund.id}",
                        )
                    )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="cash.refund.created",
                    actor=actor,
                    branch_id=appointment.branch_id,
                    target_type="refund",
                    target_id=refund.id,
                    reason=refund.reason,
                    after={
                        "payment_id": str(payment.id),
                        "amount": str(refund.amount),
                    },
                    metadata={
                        "currency": refund.currency,
                        "cashbox_id": str(cashbox.id) if cashbox else None,
                    },
                )
                result = await self._payment_result(session, payment, appointment)
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="refund.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_payment_payload(result),
                )
            return result

    async def record_manual_cash_transaction(
        self,
        *,
        actor: BookingActor,
        command: CashTransactionCommand,
    ) -> UUID:
        """Write a permitted immutable manual income, expense, adjustment, or reversal."""

        actor.require(PermissionCode.CASH_LEDGER_MANUAL_ENTRY)
        permitted_types = {
            CashTransactionType.MANUAL_INCOME,
            CashTransactionType.MANUAL_EXPENSE,
            CashTransactionType.ADJUSTMENT,
            CashTransactionType.REVERSAL,
        }
        if (
            command.type not in permitted_types
            or command.amount_delta == Decimal("0")
            or not command.reason
            or not command.idempotency_key
        ):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "cashbox_id": str(command.cashbox_id),
                "type": command.type.value,
                "amount_delta": str(command.amount_delta),
                "currency": command.currency,
                "reason": command.reason,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="cash_transaction.create",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="cash_transaction.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return UUID(str(replay["id"]))
                cashbox = await self._cashbox(
                    session,
                    organization_id=actor.organization_id,
                    cashbox_id=command.cashbox_id,
                )
                AccessPolicy.require_branch(
                    actor,
                    PermissionCode.CASH_LEDGER_MANUAL_ENTRY,
                    cashbox.branch_id,
                )
                if cashbox.currency != command.currency:
                    raise BookingDomainError(BookingErrorCode.CURRENCY_MISMATCH)
                await self._cashbox_lock(session, cashbox.id)
                shift = await self._open_cash_shift(
                    session,
                    organization_id=actor.organization_id,
                    cashbox_id=cashbox.id,
                    for_update=True,
                )
                if shift is None:
                    raise BookingDomainError(BookingErrorCode.CASH_SHIFT_NOT_OPEN)
                transaction = CashTransaction(
                    organization_id=actor.organization_id,
                    cashbox_id=cashbox.id,
                    cash_shift_id=shift.id,
                    type=command.type,
                    amount_delta=command.amount_delta,
                    currency=command.currency,
                    reason=_optional_limited_text(command.reason, 500),
                    created_by=actor.subject_id,
                    idempotency_key=command.idempotency_key,
                )
                session.add(transaction)
                await session.flush()
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="cash.ledger.manual_entry",
                    actor=actor,
                    branch_id=cashbox.branch_id,
                    target_type="cash_transaction",
                    target_id=transaction.id,
                    reason=transaction.reason,
                    after={
                        "type": transaction.type.value,
                        "amount_delta": str(transaction.amount_delta),
                    },
                    metadata={"cashbox_id": str(cashbox.id), "currency": transaction.currency},
                )
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="cash_transaction.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload={"id": str(transaction.id)},
                )
            return transaction.id

    async def record_stock_movement(
        self,
        *,
        actor: BookingActor,
        command: StockMovementCommand,
    ) -> StockMovementResult:
        """Apply a manual inventory movement and every balance delta atomically."""

        actor.require(PermissionCode.INVENTORY_MOVEMENTS_CREATE)
        if not command.lines or not command.idempotency_key:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        if command.type is StockMovementType.SERVICE_CONSUMPTION:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        aggregated: defaultdict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
        for line in command.lines:
            if line.quantity_delta == Decimal("0"):
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            aggregated[line.product_id] += line.quantity_delta
        if any(delta == Decimal("0") for delta in aggregated.values()):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        request_hash = _request_hash(
            {
                "warehouse_id": str(command.warehouse_id),
                "type": command.type.value,
                "lines": [
                    {
                        "product_id": str(product_id),
                        "quantity_delta": str(delta),
                    }
                    for product_id, delta in sorted(
                        aggregated.items(), key=lambda item: str(item[0])
                    )
                ],
                "reason": command.reason,
                "reference_type": command.reference_type,
                "reference_id": str(command.reference_id) if command.reference_id else None,
            }
        )
        async with self._database.session() as session:
            async with session.begin():
                await self._idempotency_lock(
                    session,
                    actor=actor,
                    operation="stock_movement.create",
                    key=command.idempotency_key,
                )
                replay = await self._idempotency_replay(
                    session,
                    actor=actor,
                    operation="stock_movement.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                )
                if replay is not None:
                    return _stock_movement_from_payload(replay)
                settings = await self._settings(session, actor.organization_id)
                warehouse = await self._warehouse(
                    session,
                    organization_id=actor.organization_id,
                    warehouse_id=command.warehouse_id,
                )
                AccessPolicy.require_branch(
                    actor,
                    PermissionCode.INVENTORY_MOVEMENTS_CREATE,
                    warehouse.branch_id,
                )
                products = await self._products(
                    session,
                    organization_id=actor.organization_id,
                    product_ids=tuple(aggregated),
                )
                if len(products) != len(aggregated):
                    raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
                movement = StockMovement(
                    organization_id=actor.organization_id,
                    warehouse_id=warehouse.id,
                    type=command.type,
                    reference_type=_optional_limited_text(command.reference_type, 64),
                    reference_id=command.reference_id,
                    reason=_optional_limited_text(command.reason, 500),
                    created_by=actor.subject_id,
                    idempotency_key=command.idempotency_key,
                )
                session.add(movement)
                await session.flush()
                await self._apply_stock_deltas(
                    session,
                    organization_id=actor.organization_id,
                    warehouse=warehouse,
                    deltas=aggregated,
                    products=products,
                    movement=movement,
                    allow_negative_stock=settings.allow_negative_stock,
                    actor=actor,
                    unit_costs={
                        line.product_id: line.unit_cost
                        for line in command.lines
                        if line.unit_cost is not None
                    },
                )
                result = StockMovementResult(
                    id=movement.id,
                    warehouse_id=warehouse.id,
                    type=movement.type,
                    line_count=len(aggregated),
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="inventory.movement.created",
                    actor=actor,
                    branch_id=warehouse.branch_id,
                    target_type="stock_movement",
                    target_id=movement.id,
                    reason=movement.reason,
                    after={
                        "type": movement.type.value,
                        "line_count": len(aggregated),
                    },
                    metadata={"warehouse_id": str(warehouse.id)},
                )
                await self._record_idempotency(
                    session,
                    actor=actor,
                    operation="stock_movement.create",
                    key=command.idempotency_key,
                    request_hash=request_hash,
                    response_payload=_stock_movement_payload(result),
                )
            return result

    async def _create_hold_in_transaction(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        command: HoldCommand,
        requested_start: datetime,
        enforce_upcoming_limit: bool,
        excluded_customer_reservation_id: UUID | None = None,
        required_permission: BookingPermission = BookingPermission.APPOINTMENTS_CREATE,
    ) -> HoldResult:
        """Perform the final hold checks under one outer database transaction."""

        customer_id = command.customer_id or actor.customer_id
        if customer_id is None:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        if actor.is_client and customer_id != actor.customer_id:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        settings = await self._settings(session, actor.organization_id)
        branch = await self._branch(session, actor.organization_id, command.branch_id)
        if not actor.is_client:
            AccessPolicy.require_branch(actor, required_permission, branch.id)
        service = await self._service(session, actor.organization_id, command.service_id)
        self._require_active_branch_service(branch=branch, service=service)
        customer = await self._customer(session, actor.organization_id, customer_id)
        if customer.is_blocked:
            raise BookingDomainError(BookingErrorCode.CUSTOMER_BLOCKED)
        if settings.require_client_phone and customer.normalized_phone is None:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        organization = await self._organization(session, actor.organization_id)
        timezone = self._timezone(branch, organization)
        now = require_aware(self._clock.now(), field_name="now")
        self._require_booking_window(
            starts_at=requested_start,
            timezone=timezone,
            settings=settings,
            now=now,
        )
        candidates = await self._specialist_assignments(
            session,
            organization_id=actor.organization_id,
            branch_id=branch.id,
            service=service,
            specialist_id=command.specialist_id,
            for_update=True,
        )
        if command.specialist_id is not None and not candidates:
            await self._raise_specific_specialist_error(
                session,
                organization_id=actor.organization_id,
                specialist_id=command.specialist_id,
            )
        if not candidates:
            raise BookingDomainError(BookingErrorCode.SPECIALIST_UNAVAILABLE)
        if enforce_upcoming_limit:
            await self._require_customer_upcoming_capacity(
                session,
                organization_id=actor.organization_id,
                customer_id=customer.id,
                maximum=settings.max_upcoming_appointments_per_customer,
                now=now,
            )
        selected = await self._try_create_hold_for_candidates(
            session,
            organization_id=actor.organization_id,
            branch=branch,
            organization=organization,
            service=service,
            settings=settings,
            customer=customer,
            candidates=candidates,
            requested_start=requested_start,
            owner_key=str(actor.subject_id),
            idempotency_key=command.idempotency_key,
            now=now,
            excluded_customer_reservation_id=excluded_customer_reservation_id,
        )
        if selected is None:
            raise BookingDomainError(BookingErrorCode.SLOT_TAKEN)
        return selected

    async def _try_create_hold_for_candidates(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        branch: BookingBranch,
        organization: BookingOrganization,
        service: BookingServiceModel,
        settings: BookingSettings,
        customer: Customer,
        candidates: Sequence[_EffectiveSpecialistService],
        requested_start: datetime,
        owner_key: str,
        idempotency_key: str,
        now: datetime,
        excluded_customer_reservation_id: UUID | None,
    ) -> HoldResult | None:
        """Attempt deterministic candidates through nested transactions after final checks."""

        timezone = self._timezone(branch, organization)
        ordered_candidates = sorted(candidates, key=lambda candidate: str(candidate.specialist.id))
        for candidate in ordered_candidates:
            await self._specialist_slot_lock(
                session,
                organization_id=organization_id,
                specialist_id=candidate.specialist.id,
                local_day=requested_start.astimezone(timezone).date(),
            )
            await self._expire_holds(
                session,
                organization_id=organization_id,
                specialist_id=candidate.specialist.id,
                now=now,
            )
            slot = await self._slot_at_requested_start(
                session,
                organization_id=organization_id,
                branch=branch,
                organization=organization,
                settings=settings,
                candidate=candidate,
                requested_start=requested_start,
                now=now,
            )
            if slot is None:
                continue
            if settings.prevent_customer_overlapping_appointments:
                await self._require_customer_no_conflict(
                    session,
                    organization_id=organization_id,
                    customer_id=customer.id,
                    busy_interval=TimeRange(slot.busy_starts_at, slot.busy_ends_at),
                    excluded_reservation_id=excluded_customer_reservation_id,
                )
            expires_at = now + timedelta(seconds=settings.hold_ttl_seconds)
            try:
                async with session.begin_nested():
                    reservation = SlotReservation(
                        organization_id=organization_id,
                        branch_id=branch.id,
                        specialist_id=candidate.specialist.id,
                        customer_id=customer.id,
                        service_id=service.id,
                        starts_at=slot.starts_at,
                        ends_at=slot.ends_at,
                        busy_starts_at=slot.busy_starts_at,
                        busy_ends_at=slot.busy_ends_at,
                        type=ReservationType.HOLD,
                        status=ReservationStatus.ACTIVE,
                        expires_at=expires_at,
                        owner_key=owner_key,
                        idempotency_key=idempotency_key,
                    )
                    session.add(reservation)
                    await session.flush()
                return HoldResult(
                    id=reservation.id,
                    specialist_id=reservation.specialist_id,
                    service_name=service.name,
                    specialist_name=candidate.specialist.display_name,
                    duration_minutes=candidate.duration_minutes,
                    price=candidate.price,
                    currency=service.currency,
                    starts_at=reservation.starts_at,
                    ends_at=reservation.ends_at,
                    busy_starts_at=reservation.busy_starts_at,
                    busy_ends_at=reservation.busy_ends_at,
                    expires_at=expires_at,
                )
            except IntegrityError:
                continue
        return None

    async def _appointment(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        appointment_id: UUID,
        for_update: bool,
    ) -> Appointment:
        """Load an appointment only through the verified tenant constraint."""

        statement = sa.select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.organization_id == organization_id,
        )
        if for_update:
            statement = statement.with_for_update()
        appointment = await session.scalar(statement)
        if appointment is None:
            raise BookingDomainError(BookingErrorCode.APPOINTMENT_NOT_FOUND)
        return appointment

    async def _reservation(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        reservation_id: UUID,
        for_update: bool,
        missing_code: BookingErrorCode = BookingErrorCode.APPOINTMENT_NOT_FOUND,
    ) -> SlotReservation:
        """Load a busy interval in tenant scope, optionally retaining a row lock."""

        statement = sa.select(SlotReservation).where(
            SlotReservation.id == reservation_id,
            SlotReservation.organization_id == organization_id,
        )
        if for_update:
            statement = statement.with_for_update()
        reservation = await session.scalar(statement)
        if reservation is None:
            raise BookingDomainError(missing_code)
        return reservation

    async def _require_reschedule_access(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        appointment: Appointment,
        now: datetime,
    ) -> None:
        """Authorize rescheduling before a new hold can be created or committed."""

        if appointment.status not in {
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
        }:
            raise BookingDomainError(BookingErrorCode.RESCHEDULE_NOT_ALLOWED)
        if actor.role is AccessRole.CUSTOMER:
            if actor.customer_id != appointment.customer_id:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            settings = await self._settings(session, appointment.organization_id)
            if appointment.starts_at - now < timedelta(
                minutes=settings.client_cancellation_cutoff_minutes
            ):
                raise BookingDomainError(BookingErrorCode.RESCHEDULE_NOT_ALLOWED)
            return
        AccessPolicy.require_appointment(
            actor,
            BookingPermission.APPOINTMENTS_RESCHEDULE,
            branch_id=appointment.branch_id,
            specialist_id=appointment.specialist_id,
            customer_id=appointment.customer_id,
        )

    async def _require_cancellation_access(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        appointment: Appointment,
        now: datetime,
        reason: str | None,
    ) -> None:
        """Enforce client cutoff and staff reason rules for cancellation."""

        require_transition(appointment.status, AppointmentStatus.CANCELLED)
        settings = await self._settings(session, actor.organization_id)
        if actor.role is AccessRole.CUSTOMER:
            if actor.customer_id != appointment.customer_id:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            if appointment.status not in {
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            }:
                raise BookingDomainError(BookingErrorCode.CANCELLATION_WINDOW_CLOSED)
            if appointment.starts_at - now < timedelta(
                minutes=settings.client_cancellation_cutoff_minutes
            ):
                raise BookingDomainError(BookingErrorCode.CANCELLATION_WINDOW_CLOSED)
            return
        AccessPolicy.require_appointment(
            actor,
            BookingPermission.APPOINTMENTS_CANCEL,
            branch_id=appointment.branch_id,
            specialist_id=appointment.specialist_id,
            customer_id=appointment.customer_id,
        )
        if not reason:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)

    async def _require_staff_appointment_access(
        self,
        *,
        actor: BookingActor,
        appointment: Appointment,
        permission: BookingPermission,
    ) -> None:
        """Apply the exact operation's organization/branch/self scope to one appointment."""

        AccessPolicy.require_appointment(
            actor,
            permission,
            branch_id=appointment.branch_id,
            specialist_id=appointment.specialist_id,
            customer_id=appointment.customer_id,
        )

    @staticmethod
    def _require_appointment_read_access(
        *,
        actor: BookingActor,
        appointment: Appointment,
    ) -> None:
        """Apply client/staff self-scope before returning a single appointment by UUID."""

        AccessPolicy.require_appointment(
            actor,
            BookingPermission.APPOINTMENTS_VIEW_OWN,
            branch_id=appointment.branch_id,
            specialist_id=appointment.specialist_id,
            customer_id=appointment.customer_id,
        )

    @staticmethod
    def _require_hold_owner(
        *,
        actor: BookingActor,
        hold: SlotReservation,
        permission: BookingPermission = BookingPermission.APPOINTMENTS_CREATE,
    ) -> None:
        """Prevent another subject from converting or reusing a temporary reservation."""

        if actor.is_client:
            if (
                actor.customer_id is None
                or hold.customer_id != actor.customer_id
                or hold.owner_key != str(actor.subject_id)
            ):
                raise BookingDomainError(BookingErrorCode.HOLD_OWNER_MISMATCH)
            return
        if not AccessPolicy.allows_appointment(
            actor,
            permission,
            branch_id=hold.branch_id,
            specialist_id=hold.specialist_id,
            customer_id=hold.customer_id or UUID(int=0),
        ):
            raise BookingDomainError(BookingErrorCode.HOLD_OWNER_MISMATCH)

    @staticmethod
    def _require_transition_permission(
        actor: BookingActor,
        target_status: AppointmentStatus,
    ) -> BookingPermission:
        """Map lifecycle writes to a concrete permission before querying a target record."""

        permission_by_status = {
            AppointmentStatus.CONFIRMED: BookingPermission.APPOINTMENTS_CONFIRM,
            AppointmentStatus.CHECKED_IN: BookingPermission.APPOINTMENTS_CHECK_IN,
            AppointmentStatus.COMPLETED: BookingPermission.APPOINTMENTS_COMPLETE,
            AppointmentStatus.CANCELLED: BookingPermission.APPOINTMENTS_CANCEL,
            AppointmentStatus.NO_SHOW: BookingPermission.APPOINTMENTS_NO_SHOW,
        }
        permission = permission_by_status.get(target_status)
        if permission is None:
            raise BookingDomainError(BookingErrorCode.INVALID_APPOINTMENT_STATUS_TRANSITION)
        actor.require(permission)
        return permission

    async def _cancel_appointment_in_transaction(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        appointment: Appointment,
        now: datetime,
        reason: str | None,
    ) -> None:
        """Apply cancellation invariants and all durable side effects in one transaction."""

        old_status = appointment.status
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = now
        appointment.cancelled_by = actor.subject_id
        appointment.cancellation_reason = _optional_limited_text(reason, 500)
        appointment.version += 1
        reservation = await self._reservation(
            session,
            organization_id=actor.organization_id,
            reservation_id=appointment.reservation_id,
            for_update=True,
        )
        reservation.status = ReservationStatus.RELEASED
        await self._cancel_future_reminders(
            session,
            organization_id=actor.organization_id,
            appointment_id=appointment.id,
        )
        session.add(
            AppointmentHistory(
                organization_id=actor.organization_id,
                appointment_id=appointment.id,
                event_type="cancelled",
                old_status=old_status,
                new_status=AppointmentStatus.CANCELLED,
                actor_type=actor.actor_type,
                actor_id=actor.subject_id,
                reason=_optional_limited_text(reason, 500),
                metadata_json={},
            )
        )
        settings = await self._settings(session, actor.organization_id)
        customer = await self._customer(session, actor.organization_id, appointment.customer_id)
        await self._schedule_appointment_notifications(
            session,
            organization_id=actor.organization_id,
            appointment=appointment,
            customer=customer,
            settings=settings,
            now=now,
            event_type="booking_cancelled",
        )

    async def _snapshot_service_materials(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        appointment: Appointment,
    ) -> None:
        """Freeze the active service recipe at confirmation so history cannot drift."""

        materials = (
            await session.scalars(
                sa.select(ServiceMaterial).where(
                    ServiceMaterial.organization_id == organization_id,
                    ServiceMaterial.service_id == appointment.service_id,
                    ServiceMaterial.is_active.is_(True),
                )
            )
        ).all()
        for material in materials:
            session.add(
                AppointmentMaterialSnapshot(
                    organization_id=organization_id,
                    appointment_id=appointment.id,
                    product_id=material.product_id,
                    warehouse_id=material.warehouse_id,
                    quantity_required=material.quantity_required,
                )
            )

    async def _schedule_appointment_notifications(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        appointment: Appointment,
        customer: Customer,
        settings: BookingSettings,
        now: datetime,
        event_type: str,
    ) -> None:
        """Write client/staff notifications and future reminders before transaction commit."""

        customer_identity = await self._customer_telegram_identity(
            session,
            organization_id=organization_id,
            customer_id=customer.id,
        )
        if customer_identity is not None and customer_identity.external_chat_id is not None:
            await self._enqueue_notification(
                session,
                organization_id=organization_id,
                appointment=appointment,
                event_type=event_type,
                recipient_type="customer",
                recipient_id=customer.id,
                bot_app_id=customer_identity.bot_app_id,
                chat_id=customer_identity.external_chat_id,
                locale=customer.locale,
                template_key=f"booking.{event_type}.customer",
                scheduled_at=now,
                dedupe_key=f"{event_type}:customer:{appointment.id}:{appointment.version}",
            )
        staff_bindings = (
            await session.scalars(
                sa.select(StaffTelegramBinding)
                .where(
                    StaffTelegramBinding.organization_id == organization_id,
                    StaffTelegramBinding.specialist_id == appointment.specialist_id,
                    StaffTelegramBinding.is_active.is_(True),
                    StaffTelegramBinding.telegram_chat_id.is_not(None),
                )
                .order_by(StaffTelegramBinding.created_at, StaffTelegramBinding.id)
            )
        ).all()
        for staff_binding in staff_bindings:
            if staff_binding.telegram_chat_id is None:
                continue
            await self._enqueue_notification(
                session,
                organization_id=organization_id,
                appointment=appointment,
                event_type=event_type,
                recipient_type="specialist",
                recipient_id=appointment.specialist_id,
                bot_app_id=staff_binding.bot_app_id,
                chat_id=staff_binding.telegram_chat_id,
                locale=settings.default_locale,
                template_key=f"booking.{event_type}.specialist",
                scheduled_at=now,
                dedupe_key=(
                    f"{event_type}:specialist:{staff_binding.id}:"
                    f"{appointment.id}:{appointment.version}"
                ),
            )
        if event_type not in {"booking_created", "booking_confirmed", "booking_rescheduled"}:
            return
        if customer_identity is None or customer_identity.external_chat_id is None:
            return
        for offset_minutes in settings.reminder_offsets_minutes:
            scheduled_at = appointment.starts_at - timedelta(minutes=offset_minutes)
            if scheduled_at <= now:
                continue
            await self._enqueue_notification(
                session,
                organization_id=organization_id,
                appointment=appointment,
                event_type="booking_reminder",
                recipient_type="customer",
                recipient_id=customer.id,
                bot_app_id=customer_identity.bot_app_id,
                chat_id=customer_identity.external_chat_id,
                locale=customer.locale,
                template_key="booking.reminder.customer",
                scheduled_at=scheduled_at,
                dedupe_key=(
                    f"booking_reminder:customer:{appointment.id}:"
                    f"{appointment.starts_at.isoformat()}:{offset_minutes}"
                ),
            )

    async def _enqueue_notification(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        appointment: Appointment | None,
        event_type: str,
        recipient_type: str,
        recipient_id: UUID,
        bot_app_id: str,
        chat_id: str | None,
        locale: str,
        template_key: str,
        scheduled_at: datetime,
        dedupe_key: str,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        """Add an at-least-once delivery intent; a worker sends only after commit."""

        session.add(
            NotificationOutbox(
                organization_id=organization_id,
                appointment_id=appointment.id if appointment is not None else None,
                event_type=event_type,
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                bot_app_id=bot_app_id,
                chat_id=chat_id,
                locale=locale,
                template_key=template_key,
                payload=(
                    dict(payload)
                    if payload is not None
                    else _appointment_notification_payload(appointment)
                ),
                scheduled_at=scheduled_at,
                status=OutboxStatus.PENDING,
                dedupe_key=dedupe_key,
            )
        )

    async def _customer_telegram_identity(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        customer_id: UUID,
    ) -> CustomerIdentity | None:
        """Resolve a current Telegram identity for a durable, app-bound delivery intent."""

        identity = await session.scalar(
            sa.select(CustomerIdentity)
            .where(
                CustomerIdentity.organization_id == organization_id,
                CustomerIdentity.customer_id == customer_id,
                CustomerIdentity.provider == "telegram",
            )
            .order_by(CustomerIdentity.updated_at.desc())
        )
        return identity

    async def _cancel_future_reminders(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        appointment_id: UUID,
    ) -> None:
        """Prevent canceled, completed, no-show, and rescheduled appointments from reminding."""

        await session.execute(
            sa.update(NotificationOutbox)
            .where(
                NotificationOutbox.organization_id == organization_id,
                NotificationOutbox.appointment_id == appointment_id,
                NotificationOutbox.event_type == "booking_reminder",
                NotificationOutbox.status == OutboxStatus.PENDING,
            )
            .values(status=OutboxStatus.CANCELLED)
        )

    async def _appointment_result(
        self,
        session: AsyncSession,
        appointment: Appointment,
    ) -> AppointmentResult:
        """Build payment-aware response data from aggregate queries, never relationship loads."""

        paid_amount = _decimal_or_zero(
            await session.scalar(
                sa.select(sa.func.coalesce(sa.func.sum(Payment.amount), 0)).where(
                    Payment.organization_id == appointment.organization_id,
                    Payment.appointment_id == appointment.id,
                )
            )
        )
        refunded_amount = _decimal_or_zero(
            await session.scalar(
                sa.select(sa.func.coalesce(sa.func.sum(Refund.amount), 0))
                .join(Payment, Payment.id == Refund.payment_id)
                .where(
                    Refund.organization_id == appointment.organization_id,
                    Payment.appointment_id == appointment.id,
                )
            )
        )
        payment_status = _payment_status(
            price=appointment.price_snapshot,
            paid=paid_amount,
            refunded=refunded_amount,
        )
        return AppointmentResult(
            id=appointment.id,
            public_number=appointment.public_number,
            status=appointment.status,
            branch_id=appointment.branch_id,
            customer_id=appointment.customer_id,
            specialist_id=appointment.specialist_id,
            service_id=appointment.service_id,
            starts_at=appointment.starts_at,
            ends_at=appointment.ends_at,
            service_name=appointment.service_name_snapshot,
            specialist_name=appointment.specialist_name_snapshot,
            duration_minutes=appointment.duration_minutes_snapshot,
            price=appointment.price_snapshot,
            currency=appointment.currency_snapshot,
            payment_status=payment_status,
            paid_amount=paid_amount,
            refundable_amount=max(paid_amount - refunded_amount, Decimal("0")),
            requires_manual_refund=paid_amount > refunded_amount,
        )

    async def _appointment_results(
        self,
        session: AsyncSession,
        appointments: Sequence[Appointment],
    ) -> tuple[AppointmentResult, ...]:
        """Build payment-aware list views in three bounded queries instead of per-row queries."""

        if not appointments:
            return ()
        appointment_ids = tuple(appointment.id for appointment in appointments)
        organization_id = appointments[0].organization_id
        paid_rows = (
            await session.execute(
                sa.select(
                    Payment.appointment_id,
                    sa.func.coalesce(sa.func.sum(Payment.amount), 0),
                )
                .where(
                    Payment.organization_id == organization_id,
                    Payment.appointment_id.in_(appointment_ids),
                )
                .group_by(Payment.appointment_id)
            )
        ).all()
        refunded_rows = (
            await session.execute(
                sa.select(
                    Payment.appointment_id,
                    sa.func.coalesce(sa.func.sum(Refund.amount), 0),
                )
                .join(Refund, Refund.payment_id == Payment.id)
                .where(
                    Payment.organization_id == organization_id,
                    Refund.organization_id == organization_id,
                    Payment.appointment_id.in_(appointment_ids),
                )
                .group_by(Payment.appointment_id)
            )
        ).all()
        paid_by_appointment = {
            appointment_id: _decimal_or_zero(amount) for appointment_id, amount in paid_rows
        }
        refunded_by_appointment = {
            appointment_id: _decimal_or_zero(amount) for appointment_id, amount in refunded_rows
        }
        return tuple(
            _appointment_result_from_totals(
                appointment,
                paid=paid_by_appointment.get(appointment.id, Decimal("0")),
                refunded=refunded_by_appointment.get(appointment.id, Decimal("0")),
            )
            for appointment in appointments
        )

    async def _complete_appointment_in_transaction(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        appointment: Appointment,
        now: datetime,
    ) -> None:
        """Consume frozen materials and complete an appointment as one atomic state change."""

        require_transition(appointment.status, AppointmentStatus.COMPLETED)
        settings = await self._settings(session, actor.organization_id)
        snapshots = (
            await session.scalars(
                sa.select(AppointmentMaterialSnapshot).where(
                    AppointmentMaterialSnapshot.organization_id == actor.organization_id,
                    AppointmentMaterialSnapshot.appointment_id == appointment.id,
                )
            )
        ).all()
        deltas_by_warehouse: defaultdict[UUID, defaultdict[UUID, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0"))
        )
        warehouses: dict[UUID, Warehouse] = {}
        default_warehouse: Warehouse | None = None
        for snapshot in snapshots:
            warehouse: Warehouse
            if snapshot.warehouse_id is not None:
                warehouse = await self._warehouse(
                    session,
                    organization_id=actor.organization_id,
                    warehouse_id=snapshot.warehouse_id,
                )
            else:
                if default_warehouse is None:
                    default_warehouse = await self._default_warehouse(
                        session,
                        organization_id=actor.organization_id,
                        branch_id=appointment.branch_id,
                    )
                warehouse = default_warehouse
            warehouses[warehouse.id] = warehouse
            deltas_by_warehouse[warehouse.id][snapshot.product_id] -= snapshot.quantity_required
        if deltas_by_warehouse:
            product_ids = tuple(
                {product_id for deltas in deltas_by_warehouse.values() for product_id in deltas}
            )
            products = await self._products(
                session,
                organization_id=actor.organization_id,
                product_ids=product_ids,
            )
            if len(products) != len(product_ids):
                raise BookingDomainError(BookingErrorCode.INSUFFICIENT_STOCK)
            for warehouse_id in sorted(deltas_by_warehouse, key=str):
                movement = StockMovement(
                    organization_id=actor.organization_id,
                    warehouse_id=warehouse_id,
                    type=StockMovementType.SERVICE_CONSUMPTION,
                    reference_type="appointment",
                    reference_id=appointment.id,
                    reason="appointment completion",
                    created_by=actor.subject_id,
                    idempotency_key=f"appointment_complete:{appointment.id}:{warehouse_id}",
                )
                session.add(movement)
                await session.flush()
                await self._apply_stock_deltas(
                    session,
                    organization_id=actor.organization_id,
                    warehouse=warehouses[warehouse_id],
                    deltas=deltas_by_warehouse[warehouse_id],
                    products=products,
                    movement=movement,
                    allow_negative_stock=settings.allow_negative_stock,
                    actor=actor,
                    unit_costs={},
                    low_stock_locale=settings.default_locale,
                )
                append_audit_event(
                    session,
                    organization_id=actor.organization_id,
                    action_code="inventory.consumption.recorded",
                    actor=actor,
                    branch_id=warehouses[warehouse_id].branch_id,
                    target_type="stock_movement",
                    target_id=movement.id,
                    after={
                        "appointment_id": str(appointment.id),
                        "line_count": len(deltas_by_warehouse[warehouse_id]),
                    },
                    metadata={"warehouse_id": str(warehouse_id)},
                )
        old_status = appointment.status
        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = now
        appointment.version += 1
        reservation = await self._reservation(
            session,
            organization_id=actor.organization_id,
            reservation_id=appointment.reservation_id,
            for_update=True,
        )
        reservation.status = ReservationStatus.RELEASED
        await self._cancel_future_reminders(
            session,
            organization_id=actor.organization_id,
            appointment_id=appointment.id,
        )
        session.add(
            AppointmentHistory(
                organization_id=actor.organization_id,
                appointment_id=appointment.id,
                event_type="completed",
                old_status=old_status,
                new_status=AppointmentStatus.COMPLETED,
                actor_type=actor.actor_type,
                actor_id=actor.subject_id,
                metadata_json={},
            )
        )
        customer = await self._customer(session, actor.organization_id, appointment.customer_id)
        await self._schedule_appointment_notifications(
            session,
            organization_id=actor.organization_id,
            appointment=appointment,
            customer=customer,
            settings=settings,
            now=now,
            event_type="booking_completed",
        )

    async def _cashbox(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        cashbox_id: UUID,
    ) -> Cashbox:
        """Load an active cashbox only from the current organization."""

        cashbox = await session.scalar(
            sa.select(Cashbox).where(
                Cashbox.id == cashbox_id,
                Cashbox.organization_id == organization_id,
                Cashbox.is_active.is_(True),
            )
        )
        if cashbox is None:
            raise BookingDomainError(BookingErrorCode.CASH_SHIFT_NOT_OPEN)
        return cashbox

    async def _cashbox_lock(self, session: AsyncSession, cashbox_id: UUID) -> None:
        """Serialize shift and cash-ledger state changes for one cashbox."""

        await session.execute(
            sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(f"booking:cash:{cashbox_id}")))
        )

    async def _open_cash_shift(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        cashbox_id: UUID,
        for_update: bool,
    ) -> CashShift | None:
        """Return one live shift after optional row locking."""

        statement = sa.select(CashShift).where(
            CashShift.organization_id == organization_id,
            CashShift.cashbox_id == cashbox_id,
            CashShift.status == CashShiftStatus.OPEN,
        )
        if for_update:
            statement = statement.with_for_update()
        return await session.scalar(statement)

    async def _cash_payment_shift(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        cashbox_id: UUID | None,
        currency: str,
    ) -> tuple[Cashbox, CashShift | None]:
        """Validate cashbox currency and optional open-shift policy for a cash operation."""

        if cashbox_id is None:
            raise BookingDomainError(BookingErrorCode.CASH_SHIFT_REQUIRED)
        cashbox = await self._cashbox(
            session,
            organization_id=organization_id,
            cashbox_id=cashbox_id,
        )
        if cashbox.currency != currency:
            raise BookingDomainError(BookingErrorCode.CURRENCY_MISMATCH)
        await self._cashbox_lock(session, cashbox.id)
        shift = await self._open_cash_shift(
            session,
            organization_id=organization_id,
            cashbox_id=cashbox.id,
            for_update=True,
        )
        settings = await self._settings(session, organization_id)
        if settings.require_open_cash_shift_for_cash_payment and shift is None:
            raise BookingDomainError(BookingErrorCode.CASH_SHIFT_REQUIRED)
        return cashbox, shift

    async def _payment_result(
        self,
        session: AsyncSession,
        payment: Payment,
        appointment: Appointment,
    ) -> PaymentResult:
        """Build a payment result from the same immutable aggregate policy as appointments."""

        appointment_result = await self._appointment_result(session, appointment)
        return PaymentResult(
            id=payment.id,
            appointment_id=appointment.id,
            amount=payment.amount,
            currency=payment.currency,
            payment_status=appointment_result.payment_status,
            paid_amount=appointment_result.paid_amount,
            refundable_amount=appointment_result.refundable_amount,
        )

    async def _warehouse(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        warehouse_id: UUID,
    ) -> Warehouse:
        """Load one active tenant-scoped warehouse."""

        warehouse = await session.scalar(
            sa.select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
                Warehouse.is_active.is_(True),
            )
        )
        if warehouse is None:
            raise BookingDomainError(BookingErrorCode.INSUFFICIENT_STOCK)
        return warehouse

    async def _default_warehouse(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        branch_id: UUID,
    ) -> Warehouse:
        """Resolve the single active default warehouse required by recipe rows without one."""

        warehouse = await session.scalar(
            sa.select(Warehouse).where(
                Warehouse.organization_id == organization_id,
                Warehouse.branch_id == branch_id,
                Warehouse.is_active.is_(True),
                Warehouse.is_default.is_(True),
            )
        )
        if warehouse is None:
            raise BookingDomainError(BookingErrorCode.INSUFFICIENT_STOCK)
        return warehouse

    async def _products(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        product_ids: Sequence[UUID],
    ) -> dict[UUID, Product]:
        """Batch-load products in tenant scope so stock loops cannot leak cross-tenant rows."""

        rows = (
            await session.scalars(
                sa.select(Product).where(
                    Product.organization_id == organization_id,
                    Product.id.in_(product_ids),
                )
            )
        ).all()
        return {product.id: product for product in rows}

    async def _apply_stock_deltas(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        warehouse: Warehouse,
        deltas: Mapping[UUID, Decimal],
        products: Mapping[UUID, Product],
        movement: StockMovement,
        allow_negative_stock: bool,
        actor: BookingActor,
        unit_costs: Mapping[UUID, Decimal | None],
        low_stock_locale: str = "ru",
    ) -> None:
        """Lock balances, validate stock policy, write immutable lines, and update versions."""

        for product_id, delta in sorted(deltas.items(), key=lambda item: str(item[0])):
            product = products.get(product_id)
            if product is None:
                raise BookingDomainError(BookingErrorCode.INSUFFICIENT_STOCK)
            await self._inventory_balance_lock(
                session,
                organization_id=organization_id,
                warehouse_id=warehouse.id,
                product_id=product_id,
            )
            balance = await session.scalar(
                sa.select(StockBalance)
                .where(
                    StockBalance.organization_id == organization_id,
                    StockBalance.warehouse_id == warehouse.id,
                    StockBalance.product_id == product_id,
                )
                .with_for_update()
            )
            if balance is None:
                balance = StockBalance(
                    organization_id=organization_id,
                    warehouse_id=warehouse.id,
                    product_id=product_id,
                    quantity=Decimal("0"),
                )
                session.add(balance)
                await session.flush()
            next_quantity = balance.quantity + delta
            if product.track_stock and not allow_negative_stock and next_quantity < Decimal("0"):
                raise BookingDomainError(BookingErrorCode.INSUFFICIENT_STOCK)
            balance.quantity = next_quantity
            balance.version += 1
            session.add(
                StockMovementItem(
                    organization_id=organization_id,
                    movement_id=movement.id,
                    product_id=product_id,
                    quantity_delta=delta,
                    unit_cost=unit_costs.get(product_id),
                )
            )
            if (
                product.track_stock
                and product.low_stock_threshold is not None
                and next_quantity <= product.low_stock_threshold
            ):
                await self._enqueue_low_stock_notification(
                    session,
                    organization_id=organization_id,
                    warehouse_id=warehouse.id,
                    product=product,
                    quantity=next_quantity,
                    locale=low_stock_locale,
                )

    async def _inventory_balance_lock(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        warehouse_id: UUID,
        product_id: UUID,
    ) -> None:
        """Serialize balance-row creation and final decrements across worker instances."""

        key = f"booking:stock:{organization_id}:{warehouse_id}:{product_id}"
        await session.execute(sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(key))))

    async def _enqueue_low_stock_notification(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        warehouse_id: UUID,
        product: Product,
        quantity: Decimal,
        locale: str,
    ) -> None:
        """Queue one alert per bound inventory manager without leaking inventory recipients."""

        warehouse_branch_id = await session.scalar(
            sa.select(Warehouse.branch_id).where(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
        )
        if warehouse_branch_id is None:
            return
        now = require_aware(self._clock.now(), field_name="now")
        recipient_rows = (
            await session.execute(
                sa.select(BookingMembership, StaffTelegramBinding)
                .join(
                    StaffTelegramBinding,
                    sa.and_(
                        StaffTelegramBinding.organization_id == BookingMembership.organization_id,
                        StaffTelegramBinding.membership_id == BookingMembership.id,
                        StaffTelegramBinding.is_active.is_(True),
                        StaffTelegramBinding.telegram_chat_id.is_not(None),
                    ),
                )
                .join(
                    BookingRoleAssignment,
                    sa.and_(
                        BookingRoleAssignment.membership_id == BookingMembership.id,
                        BookingRoleAssignment.is_active.is_(True),
                    ),
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
                    BookingMembership.organization_id == organization_id,
                    BookingMembership.is_active.is_(True),
                    BookingRole.is_active.is_(True),
                    BookingRolePermission.permission_code
                    == PermissionCode.INVENTORY_STOCK_VIEW.value,
                    sa.or_(
                        BookingRoleAssignment.scope == AccessScope.ORGANIZATION,
                        sa.and_(
                            BookingRoleAssignment.scope == AccessScope.BRANCH,
                            BookingRoleAssignmentBranch.branch_id == warehouse_branch_id,
                        ),
                    ),
                    sa.or_(
                        BookingRoleAssignment.starts_at.is_(None),
                        BookingRoleAssignment.starts_at <= now,
                    ),
                    sa.or_(
                        BookingRoleAssignment.ends_at.is_(None),
                        BookingRoleAssignment.ends_at > now,
                    ),
                )
                .distinct()
            )
        ).all()
        for membership, binding in recipient_rows:
            if binding.telegram_chat_id is None or membership.specialist_id is None:
                continue
            dedupe_key = f"low_stock:{warehouse_id}:{product.id}:{binding.id}"
            existing = await session.scalar(
                sa.select(NotificationOutbox.id).where(
                    NotificationOutbox.organization_id == organization_id,
                    NotificationOutbox.dedupe_key == dedupe_key,
                )
            )
            if existing is not None:
                continue
            await self._enqueue_notification(
                session,
                organization_id=organization_id,
                appointment=None,
                event_type="low_stock",
                recipient_type="inventory_manager",
                recipient_id=membership.specialist_id,
                bot_app_id=binding.bot_app_id,
                chat_id=binding.telegram_chat_id,
                locale=locale,
                template_key="booking.low_stock",
                payload={
                    "warehouse_id": str(warehouse_id),
                    "branch_id": str(warehouse_branch_id),
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "quantity": str(quantity),
                },
                scheduled_at=now,
                dedupe_key=dedupe_key,
            )

    async def _availability_for_candidates(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        branch: BookingBranch,
        settings: BookingSettings,
        candidates: Sequence[_EffectiveSpecialistService],
        date_from: date,
        date_to: date,
        now: datetime,
        customer_id: UUID | None = None,
    ) -> tuple[AvailabilityResult, ...]:
        """Batch-load schedules, exceptions, and reservations before pure slot calculation."""

        if date_to < date_from or not candidates:
            return ()
        organization = await self._organization(session, organization_id)
        timezone = self._timezone(branch, organization)
        specialist_ids = tuple(candidate.specialist.id for candidate in candidates)
        lower_bound, upper_bound = _utc_day_bounds(
            date_from=date_from,
            date_to=date_to,
            timezone=timezone,
        )
        schedules = (
            await session.scalars(
                sa.select(WorkingSchedule).where(
                    WorkingSchedule.organization_id == organization_id,
                    WorkingSchedule.branch_id == branch.id,
                    WorkingSchedule.specialist_id.in_(specialist_ids),
                    WorkingSchedule.is_active.is_(True),
                )
            )
        ).all()
        exceptions = (
            await session.scalars(
                sa.select(AvailabilityException).where(
                    AvailabilityException.organization_id == organization_id,
                    AvailabilityException.branch_id == branch.id,
                    AvailabilityException.specialist_id.in_(specialist_ids),
                    AvailabilityException.is_active.is_(True),
                    AvailabilityException.starts_at < upper_bound,
                    AvailabilityException.ends_at > lower_bound,
                )
            )
        ).all()
        reservations = (
            await session.scalars(
                sa.select(SlotReservation).where(
                    SlotReservation.organization_id == organization_id,
                    SlotReservation.branch_id == branch.id,
                    SlotReservation.specialist_id.in_(specialist_ids),
                    SlotReservation.status == ReservationStatus.ACTIVE,
                    SlotReservation.busy_starts_at < upper_bound,
                    SlotReservation.busy_ends_at > lower_bound,
                    sa.or_(
                        SlotReservation.type != ReservationType.HOLD,
                        SlotReservation.expires_at.is_(None),
                        SlotReservation.expires_at > now,
                    ),
                )
            )
        ).all()
        customer_reservations: Sequence[SlotReservation] = ()
        if customer_id is not None and settings.prevent_customer_overlapping_appointments:
            customer_reservations = (
                await session.scalars(
                    sa.select(SlotReservation).where(
                        SlotReservation.organization_id == organization_id,
                        SlotReservation.customer_id == customer_id,
                        SlotReservation.status == ReservationStatus.ACTIVE,
                        SlotReservation.busy_starts_at < upper_bound,
                        SlotReservation.busy_ends_at > lower_bound,
                        sa.or_(
                            SlotReservation.type != ReservationType.HOLD,
                            SlotReservation.expires_at.is_(None),
                            SlotReservation.expires_at > now,
                        ),
                    )
                )
            ).all()
        schedules_by_specialist: defaultdict[UUID, list[WeeklyWorkingInterval]] = defaultdict(list)
        for schedule in schedules:
            schedules_by_specialist[schedule.specialist_id].append(
                WeeklyWorkingInterval(
                    weekday=schedule.weekday,
                    local_start_time=schedule.local_start_time,
                    local_end_time=schedule.local_end_time,
                )
            )
        exceptions_by_specialist: defaultdict[UUID, list[SlotAvailabilityException]] = defaultdict(
            list
        )
        for exception in exceptions:
            exceptions_by_specialist[exception.specialist_id].append(
                SlotAvailabilityException(
                    interval=TimeRange(exception.starts_at, exception.ends_at),
                    kind=exception.type,
                )
            )
        occupied_by_specialist: defaultdict[UUID, list[TimeRange]] = defaultdict(list)
        for reservation in reservations:
            occupied_by_specialist[reservation.specialist_id].append(
                TimeRange(reservation.busy_starts_at, reservation.busy_ends_at)
            )
        customer_busy = tuple(
            TimeRange(reservation.busy_starts_at, reservation.busy_ends_at)
            for reservation in customer_reservations
        )
        result: list[AvailabilityResult] = []
        current_day = date_from
        while current_day <= date_to:
            for candidate in candidates:
                policy = _slot_policy(settings=settings, candidate=candidate)
                slots = self._slot_engine.generate(
                    local_day=current_day,
                    timezone=timezone,
                    schedules=schedules_by_specialist[candidate.specialist.id],
                    exceptions=exceptions_by_specialist[candidate.specialist.id],
                    occupied=(*occupied_by_specialist[candidate.specialist.id], *customer_busy),
                    policy=policy,
                    now=now,
                )
                result.extend(
                    AvailabilityResult(
                        specialist_id=candidate.specialist.id,
                        starts_at=slot.starts_at,
                        ends_at=slot.ends_at,
                        busy_starts_at=slot.busy_starts_at,
                        busy_ends_at=slot.busy_ends_at,
                    )
                    for slot in slots
                )
            current_day += timedelta(days=1)
        return tuple(
            sorted(
                result,
                key=lambda slot: (
                    slot.starts_at,
                    str(slot.specialist_id),
                ),
            )
        )

    async def _slot_at_requested_start(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        branch: BookingBranch,
        organization: BookingOrganization,
        settings: BookingSettings,
        candidate: _EffectiveSpecialistService,
        requested_start: datetime,
        now: datetime,
    ) -> AvailabilityResult | None:
        """Recalculate one specialist's requested slot after locks and expiration cleanup."""

        timezone = self._timezone(branch, organization)
        local_day = requested_start.astimezone(timezone).date()
        rows = await self._availability_for_candidates(
            session,
            organization_id=organization_id,
            branch=branch,
            settings=settings,
            candidates=(candidate,),
            date_from=local_day,
            date_to=local_day,
            now=now,
        )
        return next((slot for slot in rows if slot.starts_at == requested_start), None)

    async def _settings(self, session: AsyncSession, organization_id: UUID) -> BookingSettings:
        """Load required organization policy rather than using hard-coded scheduling values."""

        settings = await session.get(BookingSettings, organization_id)
        if settings is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return settings

    async def _organization(
        self,
        session: AsyncSession,
        organization_id: UUID,
    ) -> BookingOrganization:
        """Load the tenant root before using its fallback timezone."""

        organization = await session.get(BookingOrganization, organization_id)
        if organization is None or not organization.is_active:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        return organization

    async def _branch(
        self,
        session: AsyncSession,
        organization_id: UUID,
        branch_id: UUID,
    ) -> BookingBranch:
        """Fetch a branch only within the verified tenant scope."""

        branch = await session.scalar(
            sa.select(BookingBranch).where(
                BookingBranch.id == branch_id,
                BookingBranch.organization_id == organization_id,
            )
        )
        if branch is None:
            raise BookingDomainError(BookingErrorCode.BRANCH_INACTIVE)
        return branch

    async def _service(
        self,
        session: AsyncSession,
        organization_id: UUID,
        service_id: UUID,
    ) -> BookingServiceModel:
        """Fetch a service only within the verified tenant scope."""

        service = await session.scalar(
            sa.select(BookingServiceModel).where(
                BookingServiceModel.id == service_id,
                BookingServiceModel.organization_id == organization_id,
            )
        )
        if service is None:
            raise BookingDomainError(BookingErrorCode.SERVICE_INACTIVE)
        return service

    async def _customer(
        self,
        session: AsyncSession,
        organization_id: UUID,
        customer_id: UUID,
    ) -> Customer:
        """Fetch the authenticated customer's tenant-scoped record."""

        customer = await session.scalar(
            sa.select(Customer).where(
                Customer.id == customer_id,
                Customer.organization_id == organization_id,
            )
        )
        if customer is None:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        return customer

    async def _specialist_assignments(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        branch_id: UUID,
        service: BookingServiceModel,
        specialist_id: UUID | None,
        for_update: bool = False,
    ) -> tuple[_EffectiveSpecialistService, ...]:
        """Resolve eligible active specialists and their allowed per-service overrides."""

        statement = (
            sa.select(SpecialistService, Specialist)
            .join(Specialist, Specialist.id == SpecialistService.specialist_id)
            .where(
                SpecialistService.organization_id == organization_id,
                SpecialistService.branch_id == branch_id,
                SpecialistService.service_id == service.id,
                SpecialistService.is_active.is_(True),
                SpecialistService.booking_enabled.is_(True),
                Specialist.organization_id == organization_id,
                Specialist.is_active.is_(True),
                Specialist.accepts_bookings.is_(True),
                Specialist.archived_at.is_(None),
            )
            .order_by(Specialist.id)
        )
        if specialist_id is not None:
            statement = statement.where(Specialist.id == specialist_id)
        if for_update:
            statement = statement.with_for_update(of=(Specialist, SpecialistService))
        rows = (await session.execute(statement)).all()
        return tuple(
            _EffectiveSpecialistService(
                specialist=specialist,
                assignment=assignment,
                duration_minutes=assignment.custom_duration_minutes
                or service.default_duration_minutes,
                price=assignment.custom_price or service.default_price,
                buffer_before_minutes=assignment.custom_buffer_before_minutes
                if assignment.custom_buffer_before_minutes is not None
                else service.buffer_before_minutes,
                buffer_after_minutes=assignment.custom_buffer_after_minutes
                if assignment.custom_buffer_after_minutes is not None
                else service.buffer_after_minutes,
            )
            for assignment, specialist in rows
        )

    async def _raise_specific_specialist_error(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        specialist_id: UUID,
    ) -> None:
        """Return a stable reason for a requested specialist that is not eligible."""

        specialist = await session.scalar(
            sa.select(Specialist).where(
                Specialist.id == specialist_id,
                Specialist.organization_id == organization_id,
            )
        )
        if (
            specialist is None
            or not specialist.is_active
            or not specialist.accepts_bookings
            or specialist.archived_at is not None
        ):
            raise BookingDomainError(BookingErrorCode.SPECIALIST_INACTIVE)
        raise BookingDomainError(BookingErrorCode.SPECIALIST_DOES_NOT_PROVIDE_SERVICE)

    @staticmethod
    def _require_active_branch_service(
        *,
        branch: BookingBranch,
        service: BookingServiceModel,
    ) -> None:
        """Reject archived or inactive client-facing booking resources."""

        if not branch.is_active:
            raise BookingDomainError(BookingErrorCode.BRANCH_INACTIVE)
        if not service.is_active or not service.booking_enabled or service.archived_at is not None:
            raise BookingDomainError(BookingErrorCode.SERVICE_INACTIVE)

    @staticmethod
    def _timezone(branch: BookingBranch, organization: BookingOrganization) -> ZoneInfo:
        """Resolve only IANA timezone data persisted by the tenant administrator."""

        try:
            return ZoneInfo(branch.timezone or organization.default_timezone)
        except ZoneInfoNotFoundError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error

    @staticmethod
    def _require_booking_window(
        *,
        starts_at: datetime,
        timezone: ZoneInfo,
        settings: BookingSettings,
        now: datetime,
    ) -> None:
        """Enforce configurable lead and local-day horizon before any expensive query."""

        earliest = now + timedelta(minutes=settings.min_booking_lead_minutes)
        if starts_at < earliest:
            raise BookingDomainError(BookingErrorCode.BOOKING_TOO_EARLY)
        latest_day = now.astimezone(timezone).date() + timedelta(
            days=settings.max_booking_horizon_days
        )
        if starts_at.astimezone(timezone).date() > latest_day:
            raise BookingDomainError(BookingErrorCode.BOOKING_TOO_FAR_IN_FUTURE)

    async def _specialist_slot_lock(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        specialist_id: UUID,
        local_day: date,
    ) -> None:
        """Serialize same-specialist slot decisions while the exclusion constraint remains final."""

        key = f"booking:slot:{organization_id}:{specialist_id}:{local_day.isoformat()}"
        await session.execute(sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(key))))

    async def _expire_holds(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        specialist_id: UUID,
        now: datetime,
    ) -> None:
        """Release expired holds before the final availability and exclusion checks."""

        await session.execute(
            sa.update(SlotReservation)
            .where(
                SlotReservation.organization_id == organization_id,
                SlotReservation.specialist_id == specialist_id,
                SlotReservation.type == ReservationType.HOLD,
                SlotReservation.status == ReservationStatus.ACTIVE,
                SlotReservation.expires_at <= now,
            )
            .values(status=ReservationStatus.EXPIRED)
        )

    async def _require_customer_no_conflict(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        customer_id: UUID,
        busy_interval: TimeRange,
        excluded_reservation_id: UUID | None,
    ) -> None:
        """Prevent overlapping customer appointments and live holds across specialists."""

        statement = sa.select(SlotReservation.id).where(
            SlotReservation.organization_id == organization_id,
            SlotReservation.customer_id == customer_id,
            SlotReservation.status == ReservationStatus.ACTIVE,
            SlotReservation.busy_starts_at < busy_interval.end,
            SlotReservation.busy_ends_at > busy_interval.start,
        )
        if excluded_reservation_id is not None:
            statement = statement.where(SlotReservation.id != excluded_reservation_id)
        conflicting_id = await session.scalar(statement.limit(1))
        if conflicting_id is not None:
            raise BookingDomainError(BookingErrorCode.CUSTOMER_TIME_CONFLICT)

    async def _require_customer_upcoming_capacity(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        customer_id: UUID,
        maximum: int,
        now: datetime,
    ) -> None:
        """Bound active future bookings according to the tenant-owned settings row."""

        count = await session.scalar(
            sa.select(sa.func.count(Appointment.id)).where(
                Appointment.organization_id == organization_id,
                Appointment.customer_id == customer_id,
                Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES),
                Appointment.starts_at >= now,
            )
        )
        if int(count or 0) >= maximum:
            raise BookingDomainError(BookingErrorCode.CUSTOMER_BOOKING_LIMIT_REACHED)

    async def _idempotency_lock(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        operation: str,
        key: str,
    ) -> None:
        """Serialize a durable idempotency key before any side effect is generated."""

        lock_key = (
            f"booking:idempotency:{actor.organization_id}:{actor.subject_id}:{operation}:{key}"
        )
        await session.execute(sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key))))

    async def _idempotency_replay(
        self,
        session: AsyncSession,
        *,
        actor: BookingActor,
        operation: str,
        key: str,
        request_hash: str,
    ) -> dict[str, Any] | None:
        """Return a previous successful response or reject a changed reused payload."""

        record = await session.scalar(
            sa.select(BookingIdempotencyRecord)
            .where(
                BookingIdempotencyRecord.organization_id == actor.organization_id,
                BookingIdempotencyRecord.actor_id == actor.subject_id,
                BookingIdempotencyRecord.operation == operation,
                BookingIdempotencyRecord.key == key,
            )
            .with_for_update()
        )
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT)
        return record.response_payload

    @staticmethod
    async def _record_idempotency(
        session: AsyncSession,
        *,
        actor: BookingActor,
        operation: str,
        key: str,
        request_hash: str,
        response_payload: dict[str, Any],
    ) -> None:
        """Persist one replayable successful result in the same transaction as its effects."""

        session.add(
            BookingIdempotencyRecord(
                organization_id=actor.organization_id,
                actor_id=actor.subject_id,
                operation=operation,
                key=key,
                request_hash=request_hash,
                response_status=200,
                response_payload=response_payload,
            )
        )


def _slot_policy(
    *,
    settings: BookingSettings,
    candidate: _EffectiveSpecialistService,
) -> SlotPolicy:
    """Construct timing inputs from persisted settings plus the effective assignment override."""

    return SlotPolicy(
        slot_step_minutes=settings.slot_step_minutes,
        min_booking_lead_minutes=settings.min_booking_lead_minutes,
        max_booking_horizon_days=settings.max_booking_horizon_days,
        duration_minutes=candidate.duration_minutes,
        buffer_before_minutes=candidate.buffer_before_minutes,
        buffer_after_minutes=candidate.buffer_after_minutes,
    )


def _utc_day_bounds(
    *, date_from: date, date_to: date, timezone: ZoneInfo
) -> tuple[datetime, datetime]:
    """Return UTC bounds covering all requested local calendar dates."""

    lower = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone).astimezone(UTC)
    upper = datetime.combine(
        date_to + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone,
    ).astimezone(UTC)
    return lower, upper


def _request_hash(value: dict[str, object]) -> str:
    """Create a canonical hash without retaining potentially repeated request bodies."""

    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _hold_payload(result: HoldResult) -> dict[str, Any]:
    """Convert a hold result to a JSON-safe idempotency record payload."""

    return {
        "id": str(result.id),
        "specialist_id": str(result.specialist_id),
        "service_name": result.service_name,
        "specialist_name": result.specialist_name,
        "duration_minutes": result.duration_minutes,
        "price": str(result.price),
        "currency": result.currency,
        "starts_at": result.starts_at.isoformat(),
        "ends_at": result.ends_at.isoformat(),
        "busy_starts_at": result.busy_starts_at.isoformat(),
        "busy_ends_at": result.busy_ends_at.isoformat(),
        "expires_at": result.expires_at.isoformat(),
    }


def _hold_from_payload(payload: dict[str, Any]) -> HoldResult:
    """Rebuild a typed hold replay result after validating stored JSON's expected shape."""

    try:
        return HoldResult(
            id=UUID(str(payload["id"])),
            specialist_id=UUID(str(payload["specialist_id"])),
            service_name=str(payload["service_name"]),
            specialist_name=str(payload["specialist_name"]),
            duration_minutes=int(payload["duration_minutes"]),
            price=Decimal(str(payload["price"])),
            currency=str(payload["currency"]),
            starts_at=datetime.fromisoformat(str(payload["starts_at"])),
            ends_at=datetime.fromisoformat(str(payload["ends_at"])),
            busy_starts_at=datetime.fromisoformat(str(payload["busy_starts_at"])),
            busy_ends_at=datetime.fromisoformat(str(payload["busy_ends_at"])),
            expires_at=datetime.fromisoformat(str(payload["expires_at"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT) from error


def _appointment_payload(result: AppointmentResult) -> dict[str, Any]:
    """Convert a public appointment result to a durable JSON-safe replay payload."""

    return {
        "id": str(result.id),
        "public_number": result.public_number,
        "status": result.status.value,
        "branch_id": str(result.branch_id),
        "customer_id": str(result.customer_id),
        "specialist_id": str(result.specialist_id),
        "service_id": str(result.service_id),
        "starts_at": result.starts_at.isoformat(),
        "ends_at": result.ends_at.isoformat(),
        "service_name": result.service_name,
        "specialist_name": result.specialist_name,
        "duration_minutes": result.duration_minutes,
        "price": str(result.price),
        "currency": result.currency,
        "payment_status": result.payment_status,
        "paid_amount": str(result.paid_amount),
        "refundable_amount": str(result.refundable_amount),
        "requires_manual_refund": result.requires_manual_refund,
    }


def _appointment_notification_payload(appointment: Appointment | None) -> dict[str, object]:
    """Build the immutable event data required by notification templates at send time."""

    if appointment is None:
        return {}
    return {
        "appointment_id": str(appointment.id),
        "public_number": appointment.public_number,
        "starts_at": appointment.starts_at.isoformat(),
        "service_name": appointment.service_name_snapshot,
        "specialist_name": appointment.specialist_name_snapshot,
    }


def _appointment_from_payload(payload: dict[str, Any]) -> AppointmentResult:
    """Rebuild an appointment replay result while rejecting malformed stored JSON."""

    try:
        return AppointmentResult(
            id=UUID(str(payload["id"])),
            public_number=str(payload["public_number"]),
            status=AppointmentStatus(str(payload["status"])),
            branch_id=UUID(str(payload["branch_id"])),
            customer_id=UUID(str(payload["customer_id"])),
            specialist_id=UUID(str(payload["specialist_id"])),
            service_id=UUID(str(payload["service_id"])),
            starts_at=datetime.fromisoformat(str(payload["starts_at"])),
            ends_at=datetime.fromisoformat(str(payload["ends_at"])),
            service_name=str(payload["service_name"]),
            specialist_name=str(payload["specialist_name"]),
            duration_minutes=int(payload["duration_minutes"]),
            price=Decimal(str(payload["price"])),
            currency=str(payload["currency"]),
            payment_status=str(payload["payment_status"]),
            paid_amount=Decimal(str(payload["paid_amount"])),
            refundable_amount=Decimal(str(payload["refundable_amount"])),
            requires_manual_refund=bool(payload["requires_manual_refund"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT) from error


def _public_appointment_number(appointment_id: UUID, now: datetime) -> str:
    """Generate a human-shareable identifier without exposing internal sequence semantics."""

    return f"B-{now:%Y%m%d}-{appointment_id.hex[:8].upper()}"


def _duration_minutes(starts_at: datetime, ends_at: datetime) -> int:
    """Return a persisted positive service duration from exact UTC timestamps."""

    return int((ends_at - starts_at).total_seconds() // 60)


def _optional_limited_text(value: str | None, maximum_length: int) -> str | None:
    """Trim optional user input to the database's declared safe maximum."""

    if value is None:
        return None
    normalized = value.strip()
    return normalized[:maximum_length] if normalized else None


def _apply_transition_timestamp(
    *,
    appointment: Appointment,
    target_status: AppointmentStatus,
    now: datetime,
) -> None:
    """Set exactly the lifecycle timestamp corresponding to one allowed target status."""

    if target_status is AppointmentStatus.CONFIRMED:
        appointment.confirmed_at = now
    elif target_status is AppointmentStatus.CHECKED_IN:
        appointment.checked_in_at = now
    elif target_status is AppointmentStatus.COMPLETED:
        appointment.completed_at = now
    elif target_status is AppointmentStatus.NO_SHOW:
        appointment.no_show_at = now


def _decimal_or_zero(value: Decimal | int | None) -> Decimal:
    """Normalize database aggregate values without introducing binary float arithmetic."""

    if value is None:
        return Decimal("0")
    return Decimal(value)


def _payment_status(*, price: Decimal, paid: Decimal, refunded: Decimal) -> str:
    """Derive the documented payment status from immutable payment/refund totals."""

    if paid == Decimal("0"):
        return "unpaid"
    if refunded >= paid:
        return "refunded"
    if refunded > Decimal("0"):
        return "partially_refunded"
    if paid >= price:
        return "paid"
    return "partial"


def _appointment_result_from_totals(
    appointment: Appointment,
    *,
    paid: Decimal,
    refunded: Decimal,
) -> AppointmentResult:
    """Build an appointment result from values obtained through a grouped aggregate query."""

    return AppointmentResult(
        id=appointment.id,
        public_number=appointment.public_number,
        status=appointment.status,
        branch_id=appointment.branch_id,
        customer_id=appointment.customer_id,
        specialist_id=appointment.specialist_id,
        service_id=appointment.service_id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        service_name=appointment.service_name_snapshot,
        specialist_name=appointment.specialist_name_snapshot,
        duration_minutes=appointment.duration_minutes_snapshot,
        price=appointment.price_snapshot,
        currency=appointment.currency_snapshot,
        payment_status=_payment_status(
            price=appointment.price_snapshot,
            paid=paid,
            refunded=refunded,
        ),
        paid_amount=paid,
        refundable_amount=max(paid - refunded, Decimal("0")),
        requires_manual_refund=paid > refunded,
    )


def _customer_view(customer: Customer) -> dict[str, Any]:
    """Expose customer fields appropriate for the booking client or back-office list."""

    return {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "phone": customer.normalized_phone,
        "locale": customer.locale,
        "timezone": customer.timezone,
        "is_blocked": customer.is_blocked,
    }


def _branch_view(branch: BookingBranch) -> dict[str, Any]:
    """Map a branch without leaking persistence-only metadata."""

    return {
        "id": branch.id,
        "name": branch.name,
        "address": branch.address,
        "timezone": branch.timezone,
        "phone": branch.phone,
        "is_active": branch.is_active,
    }


def _category_view(category: Any) -> dict[str, Any]:
    """Map a category while keeping ORM types private to this module layer."""

    return {
        "id": category.id,
        "name": category.name,
        "sort_order": category.sort_order,
        "is_active": category.is_active,
    }


def _service_view(service: BookingServiceModel) -> dict[str, Any]:
    """Map a public service definition, not mutable ORM state."""

    return {
        "id": service.id,
        "category_id": service.category_id,
        "name": service.name,
        "description": service.description,
        "duration_minutes": service.default_duration_minutes,
        "price": service.default_price,
        "currency": service.currency,
        "buffer_before_minutes": service.buffer_before_minutes,
        "buffer_after_minutes": service.buffer_after_minutes,
        "is_active": service.is_active,
        "booking_enabled": service.booking_enabled,
        "sort_order": service.sort_order,
    }


def _specialist_view(specialist: Specialist) -> dict[str, Any]:
    """Map a specialist selection card without exposing staff access identifiers."""

    return {
        "id": specialist.id,
        "display_name": specialist.display_name,
        "description": specialist.description,
        "is_active": specialist.is_active,
        "accepts_bookings": specialist.accepts_bookings,
    }


def _cash_shift_result(shift: CashShift) -> CashShiftResult:
    """Expose immutable shift-state fields without leaking cashbox implementation details."""

    return CashShiftResult(
        id=shift.id,
        cashbox_id=shift.cashbox_id,
        status=shift.status.value,
        opening_amount=shift.opening_amount,
        expected_closing_amount=shift.expected_closing_amount,
        actual_closing_amount=shift.actual_closing_amount,
        difference=shift.difference,
    )


def _cash_shift_payload(result: CashShiftResult) -> dict[str, Any]:
    """Serialize one replayable shift result."""

    return {
        "id": str(result.id),
        "cashbox_id": str(result.cashbox_id),
        "status": result.status,
        "opening_amount": str(result.opening_amount),
        "expected_closing_amount": (
            str(result.expected_closing_amount)
            if result.expected_closing_amount is not None
            else None
        ),
        "actual_closing_amount": (
            str(result.actual_closing_amount) if result.actual_closing_amount is not None else None
        ),
        "difference": str(result.difference) if result.difference is not None else None,
    }


def _cash_shift_from_payload(payload: dict[str, Any]) -> CashShiftResult:
    """Rebuild a stored idempotent shift result safely."""

    try:
        return CashShiftResult(
            id=UUID(str(payload["id"])),
            cashbox_id=UUID(str(payload["cashbox_id"])),
            status=str(payload["status"]),
            opening_amount=Decimal(str(payload["opening_amount"])),
            expected_closing_amount=_optional_decimal(payload["expected_closing_amount"]),
            actual_closing_amount=_optional_decimal(payload["actual_closing_amount"]),
            difference=_optional_decimal(payload["difference"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT) from error


def _payment_payload(result: PaymentResult) -> dict[str, Any]:
    """Serialize a payment replay result including its current appointment financial state."""

    return {
        "id": str(result.id),
        "appointment_id": str(result.appointment_id),
        "amount": str(result.amount),
        "currency": result.currency,
        "payment_status": result.payment_status,
        "paid_amount": str(result.paid_amount),
        "refundable_amount": str(result.refundable_amount),
    }


def _payment_from_payload(payload: dict[str, Any]) -> PaymentResult:
    """Rebuild an idempotent payment/refund response from durable JSON."""

    try:
        return PaymentResult(
            id=UUID(str(payload["id"])),
            appointment_id=UUID(str(payload["appointment_id"])),
            amount=Decimal(str(payload["amount"])),
            currency=str(payload["currency"]),
            payment_status=str(payload["payment_status"]),
            paid_amount=Decimal(str(payload["paid_amount"])),
            refundable_amount=Decimal(str(payload["refundable_amount"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT) from error


def _stock_movement_payload(result: StockMovementResult) -> dict[str, Any]:
    """Serialize one manual stock movement result for idempotency replay."""

    return {
        "id": str(result.id),
        "warehouse_id": str(result.warehouse_id),
        "type": result.type.value,
        "line_count": result.line_count,
    }


def _stock_movement_from_payload(payload: dict[str, Any]) -> StockMovementResult:
    """Rebuild a stock movement replay result safely."""

    try:
        return StockMovementResult(
            id=UUID(str(payload["id"])),
            warehouse_id=UUID(str(payload["warehouse_id"])),
            type=StockMovementType(str(payload["type"])),
            line_count=int(payload["line_count"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise BookingDomainError(BookingErrorCode.IDEMPOTENCY_CONFLICT) from error


def _optional_decimal(value: object) -> Decimal | None:
    """Decode nullable Decimal string values stored by the idempotency layer."""

    return Decimal(str(value)) if value is not None else None
