"""High-value pure booking invariants that must hold independently of PostgreSQL."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.modules.booking.domain.enums import AppointmentStatus, AvailabilityExceptionType
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.domain.slot_engine import (
    AvailabilityException,
    SlotEngine,
    SlotPolicy,
    WeeklyWorkingInterval,
)
from app.modules.booking.domain.state_machine import is_active_appointment, require_transition
from app.modules.booking.domain.value_objects import TimeRange


def _utc(hour: int, minute: int = 0) -> datetime:
    """Build a concise aware UTC time for deterministic slot fixtures."""

    return datetime(2026, 1, 5, hour, minute, tzinfo=UTC)


def _policy() -> SlotPolicy:
    """Return a policy whose buffers make interval boundaries visible in assertions."""

    return SlotPolicy(
        slot_step_minutes=15,
        min_booking_lead_minutes=0,
        max_booking_horizon_days=60,
        duration_minutes=30,
        buffer_before_minutes=5,
        buffer_after_minutes=10,
    )


def test_slot_engine_uses_half_open_busy_buffers_for_conflicts() -> None:
    """A conflict touching the first slot end does not block it, but blocks the next one."""

    slots = SlotEngine().generate(
        local_day=date(2026, 1, 5),
        timezone=ZoneInfo("UTC"),
        schedules=(
            WeeklyWorkingInterval(weekday=0, local_start_time=time(9), local_end_time=time(10)),
        ),
        exceptions=(),
        occupied=(TimeRange(_utc(9, 45), _utc(10)),),
        policy=_policy(),
        now=_utc(8),
    )

    assert [(slot.starts_at, slot.ends_at) for slot in slots] == [(_utc(9, 5), _utc(9, 35))]
    assert slots[0].busy_interval == TimeRange(_utc(9), _utc(9, 45))


def test_slot_engine_unavailable_exception_overrides_weekly_schedule() -> None:
    """An explicit UTC closure removes only its overlapping part from generated availability."""

    slots = SlotEngine().generate(
        local_day=date(2026, 1, 5),
        timezone=ZoneInfo("UTC"),
        schedules=(
            WeeklyWorkingInterval(weekday=0, local_start_time=time(9), local_end_time=time(10)),
        ),
        exceptions=(
            AvailabilityException(
                interval=TimeRange(_utc(9), _utc(9, 30)),
                kind=AvailabilityExceptionType.UNAVAILABLE,
            ),
        ),
        occupied=(),
        policy=SlotPolicy(
            slot_step_minutes=15,
            min_booking_lead_minutes=0,
            max_booking_horizon_days=60,
            duration_minutes=15,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
        ),
        now=_utc(8),
    )

    assert [slot.starts_at for slot in slots] == [_utc(9, 30), _utc(9, 45)]


def test_slot_engine_rejects_nonexistent_dst_schedule_time() -> None:
    """A local schedule in a spring-forward gap cannot silently become a different UTC time."""

    with pytest.raises(ValueError, match="nonexistent local time"):
        SlotEngine().generate(
            local_day=date(2026, 3, 29),
            timezone=ZoneInfo("Europe/Berlin"),
            schedules=(
                WeeklyWorkingInterval(weekday=6, local_start_time=time(2), local_end_time=time(3)),
            ),
            exceptions=(),
            occupied=(),
            policy=_policy(),
            now=datetime(2026, 3, 28, 12, tzinfo=UTC),
        )


def test_lifecycle_rejects_terminal_or_skipped_transitions() -> None:
    """Only state-machine transitions keep reservations and operational events coherent."""

    require_transition(AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
    assert is_active_appointment(AppointmentStatus.CHECKED_IN)
    assert not is_active_appointment(AppointmentStatus.COMPLETED)

    with pytest.raises(BookingDomainError) as raised:
        require_transition(AppointmentStatus.PENDING, AppointmentStatus.COMPLETED)

    assert raised.value.code is BookingErrorCode.INVALID_APPOINTMENT_STATUS_TRANSITION
