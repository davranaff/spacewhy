"""Typed command and result objects for booking application use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.booking.domain.enums import (
    AppointmentSource,
    AppointmentStatus,
    CashTransactionType,
    PaymentMethod,
    StockMovementType,
)


@dataclass(frozen=True, slots=True)
class AvailabilityQuery:
    """Requested availability scope, always paired with a verified tenant actor."""

    branch_id: UUID
    service_id: UUID
    date_from: date
    date_to: date
    specialist_id: UUID | None = None
    customer_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class HoldCommand:
    """A client-selected time; commercial fields are intentionally absent."""

    branch_id: UUID
    service_id: UUID
    starts_at: datetime
    idempotency_key: str
    specialist_id: UUID | None = None
    customer_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ConfirmAppointmentCommand:
    """Confirm a verified hold into one immutable appointment."""

    hold_id: UUID
    customer_note: str | None
    idempotency_key: str
    source: AppointmentSource


@dataclass(frozen=True, slots=True)
class CancelAppointmentCommand:
    """Cancel an appointment with caller-appropriate reason requirements."""

    appointment_id: UUID
    idempotency_key: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RescheduleCommitCommand:
    """Atomically replace an appointment reservation with a client-owned hold."""

    appointment_id: UUID
    hold_id: UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class StatusTransitionCommand:
    """An allowed staff/admin lifecycle transition."""

    appointment_id: UUID
    target_status: AppointmentStatus
    idempotency_key: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PaymentCommand:
    """Create one immutable payment against a scoped appointment."""

    appointment_id: UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    idempotency_key: str
    cashbox_id: UUID | None = None
    external_reference: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class RefundCommand:
    """Create one immutable refund against one payment."""

    payment_id: UUID
    amount: Decimal
    currency: str
    reason: str
    idempotency_key: str
    cashbox_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CashShiftCommand:
    """Open or close a cash shift with exact user-entered amounts."""

    cashbox_id: UUID
    amount: Decimal
    idempotency_key: str
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class StockMovementLine:
    """One immutable stock delta line."""

    product_id: UUID
    quantity_delta: Decimal
    unit_cost: Decimal | None = None


@dataclass(frozen=True, slots=True)
class StockMovementCommand:
    """Create an inventory receipt, write-off, adjustment, or reversal."""

    warehouse_id: UUID
    type: StockMovementType
    lines: tuple[StockMovementLine, ...]
    idempotency_key: str
    reason: str | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CashTransactionCommand:
    """Manual cash transaction accepted only for a currently open cash shift."""

    cashbox_id: UUID
    type: CashTransactionType
    amount_delta: Decimal
    currency: str
    idempotency_key: str
    reason: str


@dataclass(frozen=True, slots=True)
class PriceOverrideCommand:
    """Audited administrative snapshot price override for one historical appointment."""

    appointment_id: UUID
    price: Decimal
    reason: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class HoldResult:
    """Safely serializable hold result returned to a client after DB commit."""

    id: UUID
    specialist_id: UUID
    service_name: str
    specialist_name: str
    duration_minutes: int
    price: Decimal
    currency: str
    starts_at: datetime
    ends_at: datetime
    busy_starts_at: datetime
    busy_ends_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AppointmentResult:
    """Canonical public appointment representation with frozen commercial snapshots."""

    id: UUID
    public_number: str
    status: AppointmentStatus
    branch_id: UUID
    customer_id: UUID
    specialist_id: UUID
    service_id: UUID
    starts_at: datetime
    ends_at: datetime
    service_name: str
    specialist_name: str
    duration_minutes: int
    price: Decimal
    currency: str
    payment_status: str
    paid_amount: Decimal
    refundable_amount: Decimal
    requires_manual_refund: bool = False


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    """A time choice belonging to a real active specialist."""

    specialist_id: UUID
    starts_at: datetime
    ends_at: datetime
    busy_starts_at: datetime
    busy_ends_at: datetime


@dataclass(frozen=True, slots=True)
class AnalyticsQuery:
    """Bounded tenant-scoped analytics filter."""

    date_from: date
    date_to: date
    timezone: str
    branch_id: UUID | None = None
    specialist_id: UUID | None = None
    service_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CashShiftResult:
    """Immutable cash shift summary after an open or close command."""

    id: UUID
    cashbox_id: UUID
    status: str
    opening_amount: Decimal
    expected_closing_amount: Decimal | None
    actual_closing_amount: Decimal | None
    difference: Decimal | None


@dataclass(frozen=True, slots=True)
class PaymentResult:
    """Immutable payment or refund-safe balance summary returned after a cash operation."""

    id: UUID
    appointment_id: UUID
    amount: Decimal
    currency: str
    payment_status: str
    paid_amount: Decimal
    refundable_amount: Decimal


@dataclass(frozen=True, slots=True)
class StockMovementResult:
    """Immutable movement header summary after balances have been atomically updated."""

    id: UUID
    warehouse_id: UUID
    type: StockMovementType
    line_count: int
