"""Pure worker safeguards for stale asynchronous booking notifications."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.modules.booking.domain.enums import AccessScope, AppointmentStatus
from app.modules.booking.infrastructure.jobs.worker import (
    appointment_event_is_current,
    branch_timezone,
    local_day_bounds,
    scope_allows_notification,
)
from app.modules.booking.infrastructure.persistence.models import (
    Appointment,
    BookingBranch,
    BookingOrganization,
)


def _appointment(*, status: AppointmentStatus, starts_at: datetime) -> Appointment:
    """Build the minimum ORM instance used by a pure pre-send status guard."""

    return Appointment(status=status, starts_at=starts_at)


def test_reminder_is_suppressed_after_reschedule_or_terminal_transition() -> None:
    """The outbox may be at-least-once, but it must not send stale appointment state."""

    original_start = datetime(2026, 1, 5, 12, tzinfo=UTC)
    rescheduled = _appointment(
        status=AppointmentStatus.CONFIRMED,
        starts_at=datetime(2026, 1, 5, 13, tzinfo=UTC),
    )
    cancelled = _appointment(status=AppointmentStatus.CANCELLED, starts_at=original_start)
    payload = {"starts_at": original_start.isoformat()}

    assert not appointment_event_is_current(
        event_type="booking_reminder",
        appointment=rescheduled,
        payload=payload,
        now=datetime(2026, 1, 5, 9, tzinfo=UTC),
    )
    assert not appointment_event_is_current(
        event_type="booking_reminder",
        appointment=cancelled,
        payload=payload,
        now=datetime(2026, 1, 5, 9, tzinfo=UTC),
    )


def test_cancellation_notification_is_sent_only_for_current_cancelled_state() -> None:
    """A delayed cancellation event cannot be emitted after a record was changed unexpectedly."""

    appointment = _appointment(
        status=AppointmentStatus.CONFIRMED,
        starts_at=datetime(2026, 1, 5, 12, tzinfo=UTC),
    )

    assert not appointment_event_is_current(
        event_type="booking_cancelled",
        appointment=appointment,
        payload={},
        now=datetime(2026, 1, 5, 9, tzinfo=UTC),
    )


def test_local_day_bounds_follow_dst_without_a_fixed_24_hour_assumption() -> None:
    """Daily agenda queries use half-open UTC bounds for the branch's local calendar day."""

    starts_at, ends_at = local_day_bounds(date(2026, 3, 29), ZoneInfo("Europe/Berlin"))

    assert starts_at == datetime(2026, 3, 28, 23, tzinfo=UTC)
    assert ends_at == datetime(2026, 3, 29, 22, tzinfo=UTC)


def test_daily_agenda_prefers_the_branch_timezone_over_the_organization_default() -> None:
    """A multi-branch worker must not form a branch agenda on the tenant's calendar day."""

    timezone = branch_timezone(
        branch=BookingBranch(timezone="Pacific/Auckland"),
        organization=BookingOrganization(default_timezone="UTC"),
    )

    assert timezone == ZoneInfo("Pacific/Auckland")


def test_staff_notification_scope_never_treats_self_as_inventory_branch_access() -> None:
    """Delayed stock alerts remain blocked when only a specialist self-scope is active."""

    assert (
        scope_allows_notification(
            scope_rows=[(AccessScope.SELF, None)],
            target_branch_id=None,
            specialist_id=None,
            recipient_type="inventory_manager",
        )
        is False
    )
