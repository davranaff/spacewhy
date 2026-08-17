"""Deterministic, timezone-safe available-slot calculation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.modules.booking.domain.enums import AvailabilityExceptionType
from app.modules.booking.domain.value_objects import TimeRange, require_aware


@dataclass(frozen=True, slots=True)
class WeeklyWorkingInterval:
    """One local working interval for one weekday, with no overnight ambiguity."""

    weekday: int
    local_start_time: time
    local_end_time: time

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be in [0, 6].")
        if self.local_start_time.tzinfo is not None or self.local_end_time.tzinfo is not None:
            raise ValueError("Working schedule times must be timezone-naive local wall times.")
        if self.local_end_time <= self.local_start_time:
            raise ValueError(
                "Overnight schedules must be normalized into two same-day working intervals."
            )


@dataclass(frozen=True, slots=True)
class AvailabilityException:
    """An explicit UTC exception that subtracts or adds an availability interval."""

    interval: TimeRange
    kind: AvailabilityExceptionType


@dataclass(frozen=True, slots=True)
class SlotPolicy:
    """All configurable booking timing inputs for one organization/branch."""

    slot_step_minutes: int
    min_booking_lead_minutes: int
    max_booking_horizon_days: int
    duration_minutes: int
    buffer_before_minutes: int
    buffer_after_minutes: int

    def __post_init__(self) -> None:
        if self.slot_step_minutes <= 0:
            raise ValueError("slot_step_minutes must be positive.")
        if self.min_booking_lead_minutes < 0:
            raise ValueError("min_booking_lead_minutes cannot be negative.")
        if self.max_booking_horizon_days < 0:
            raise ValueError("max_booking_horizon_days cannot be negative.")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive.")
        if self.buffer_before_minutes < 0 or self.buffer_after_minutes < 0:
            raise ValueError("Buffers cannot be negative.")

    @property
    def service_duration(self) -> timedelta:
        """Return the effective service duration."""

        return timedelta(minutes=self.duration_minutes)

    @property
    def buffer_before(self) -> timedelta:
        """Return configured pre-service busy buffer."""

        return timedelta(minutes=self.buffer_before_minutes)

    @property
    def buffer_after(self) -> timedelta:
        """Return configured post-service busy buffer."""

        return timedelta(minutes=self.buffer_after_minutes)


@dataclass(frozen=True, slots=True)
class AvailableSlot:
    """A returned customer-visible interval plus its internal busy range."""

    starts_at: datetime
    ends_at: datetime
    busy_starts_at: datetime
    busy_ends_at: datetime

    @property
    def service_interval(self) -> TimeRange:
        """Return the actual service half-open interval."""

        return TimeRange(self.starts_at, self.ends_at)

    @property
    def busy_interval(self) -> TimeRange:
        """Return the buffer-inclusive half-open interval."""

        return TimeRange(self.busy_starts_at, self.busy_ends_at)


class SlotEngine:
    """Generate slots from local schedule input and UTC conflict intervals."""

    def generate(
        self,
        *,
        local_day: date,
        timezone: ZoneInfo,
        schedules: Sequence[WeeklyWorkingInterval],
        exceptions: Iterable[AvailabilityException],
        occupied: Iterable[TimeRange],
        policy: SlotPolicy,
        now: datetime,
    ) -> tuple[AvailableSlot, ...]:
        """Return deterministic non-overlapping choices for one specialist and local day."""

        now_utc = require_aware(now, field_name="now")
        day_start_local = _safe_local_datetime(local_day, time.min, timezone)
        day_end_local = _safe_local_datetime(
            local_day + timedelta(days=1),
            time.min,
            timezone,
        )
        day_range = TimeRange(day_start_local, day_end_local)
        working = tuple(
            TimeRange(
                _safe_local_datetime(local_day, schedule.local_start_time, timezone),
                _safe_local_datetime(local_day, schedule.local_end_time, timezone),
            )
            for schedule in schedules
            if schedule.weekday == local_day.weekday()
        )
        available = _merge_ranges(working)
        for exception in exceptions:
            clipped = _clip(exception.interval, day_range)
            if clipped is None:
                continue
            if exception.kind is AvailabilityExceptionType.UNAVAILABLE:
                available = _subtract_range_set(available, clipped)
            else:
                available = _merge_ranges((*available, clipped))
        busy_ranges = tuple(conflict for conflict in occupied if conflict.overlaps(day_range))
        earliest = now_utc + timedelta(minutes=policy.min_booking_lead_minutes)
        horizon = now_utc + timedelta(days=policy.max_booking_horizon_days)
        slots: list[AvailableSlot] = []
        step = timedelta(minutes=policy.slot_step_minutes)
        for working_range in available:
            candidate_busy_start = _ceil_datetime(working_range.start, step)
            while candidate_busy_start < working_range.end:
                service_start = candidate_busy_start + policy.buffer_before
                service_end = service_start + policy.service_duration
                busy_end = service_end + policy.buffer_after
                candidate_busy = TimeRange(candidate_busy_start, busy_end)
                if candidate_busy.end > working_range.end:
                    break
                if (
                    service_start >= earliest
                    and service_start <= horizon
                    and not any(candidate_busy.overlaps(conflict) for conflict in busy_ranges)
                ):
                    slots.append(
                        AvailableSlot(
                            starts_at=service_start,
                            ends_at=service_end,
                            busy_starts_at=candidate_busy.start,
                            busy_ends_at=candidate_busy.end,
                        )
                    )
                candidate_busy_start += step
        return tuple(slots)


def _safe_local_datetime(local_day: date, local_time: time, timezone: ZoneInfo) -> datetime:
    """Convert one wall time to UTC, rejecting nonexistent DST times deterministically."""

    local_value = datetime.combine(local_day, local_time, tzinfo=timezone)
    round_trip = local_value.astimezone(UTC).astimezone(timezone)
    if round_trip.replace(tzinfo=None) != local_value.replace(tzinfo=None):
        raise ValueError("Schedule contains a nonexistent local time due to a DST transition.")
    return local_value.astimezone(UTC)


def _ceil_datetime(value: datetime, step: timedelta) -> datetime:
    """Round UTC values upward to a slot step aligned to the local day's UTC start."""

    seconds = int(step.total_seconds())
    timestamp = int(value.timestamp())
    remainder = timestamp % seconds
    return value if remainder == 0 else value + timedelta(seconds=seconds - remainder)


def _merge_ranges(ranges: Iterable[TimeRange]) -> tuple[TimeRange, ...]:
    """Merge touching intervals while retaining half-open semantics."""

    ordered = sorted(ranges, key=lambda value: (value.start, value.end))
    result: list[TimeRange] = []
    for current in ordered:
        if not result or result[-1].end < current.start:
            result.append(current)
            continue
        previous = result[-1]
        result[-1] = TimeRange(previous.start, max(previous.end, current.end))
    return tuple(result)


def _subtract_range_set(ranges: Iterable[TimeRange], excluded: TimeRange) -> tuple[TimeRange, ...]:
    """Remove one half-open interval from every provided working interval."""

    result: list[TimeRange] = []
    for current in ranges:
        if not current.overlaps(excluded):
            result.append(current)
            continue
        if current.start < excluded.start:
            result.append(TimeRange(current.start, min(current.end, excluded.start)))
        if excluded.end < current.end:
            result.append(TimeRange(max(current.start, excluded.end), current.end))
    return tuple(result)


def _clip(value: TimeRange, outer: TimeRange) -> TimeRange | None:
    """Return the intersection or no value when two intervals are disjoint."""

    if not value.overlaps(outer):
        return None
    return TimeRange(max(value.start, outer.start), min(value.end, outer.end))
