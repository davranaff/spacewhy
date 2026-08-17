"""Explicit appointment lifecycle rules with no persistence or framework imports."""

from __future__ import annotations

from collections.abc import Mapping

from app.modules.booking.domain.enums import AppointmentStatus
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode

_ALLOWED_TRANSITIONS: Mapping[AppointmentStatus, frozenset[AppointmentStatus]] = {
    AppointmentStatus.PENDING: frozenset(
        {
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CANCELLED,
        }
    ),
    AppointmentStatus.CONFIRMED: frozenset(
        {
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
            AppointmentStatus.NO_SHOW,
        }
    ),
    AppointmentStatus.CHECKED_IN: frozenset(
        {
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELLED,
        }
    ),
    AppointmentStatus.COMPLETED: frozenset(),
    AppointmentStatus.CANCELLED: frozenset(),
    AppointmentStatus.NO_SHOW: frozenset(),
}


def can_transition(current: AppointmentStatus, target: AppointmentStatus) -> bool:
    """Return whether the durable status machine permits a transition."""

    return target in _ALLOWED_TRANSITIONS[current]


def require_transition(current: AppointmentStatus, target: AppointmentStatus) -> None:
    """Reject illegal state changes with the stable contract error code."""

    if not can_transition(current, target):
        raise BookingDomainError(BookingErrorCode.INVALID_APPOINTMENT_STATUS_TRANSITION)


def is_active_appointment(status: AppointmentStatus) -> bool:
    """Return whether an appointment still occupies its reservation interval."""

    return status in {
        AppointmentStatus.PENDING,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
    }
