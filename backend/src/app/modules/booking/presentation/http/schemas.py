"""Pydantic transport schemas; business validation remains in booking application services."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import (
    AppointmentResult,
    AvailabilityResult,
    CashShiftResult,
    HoldResult,
    PaymentResult,
    StockMovementResult,
)
from app.modules.booking.application.permissions import PermissionCode
from app.modules.booking.domain.enums import (
    AccessScope,
    AppointmentStatus,
    CashTransactionType,
    PaymentMethod,
    StockMovementType,
)


class _Schema(BaseModel):
    """Reject undeclared transport fields before application input construction."""

    model_config = ConfigDict(extra="forbid")


class TelegramAuthRequest(_Schema):
    """Telegram WebApp authentication input; it contains no trusted role or tenant fields."""

    bot_app_id: str = Field(min_length=1, max_length=63, pattern=r"^[a-z][a-z0-9_]{0,62}$")
    init_data: str = Field(min_length=1, max_length=16_384)


class SessionActorResponse(_Schema):
    """Display-only signed actor context returned after server-side WebApp verification."""

    organization_id: UUID
    role: str
    customer_id: UUID | None
    specialist_id: UUID | None
    permissions: list[str]

    @classmethod
    def from_actor(cls, actor: BookingActor) -> SessionActorResponse:
        """Avoid exposing an internal subject ID as a client authorization knob."""

        return cls(
            organization_id=actor.organization_id,
            role=actor.role.value,
            customer_id=actor.customer_id,
            specialist_id=actor.specialist_id,
            permissions=sorted(actor.permission_codes),
        )


class SessionResponse(_Schema):
    """Bearer session issued only after verified initData and server-side grant lookup."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    actor: SessionActorResponse


class HoldRequest(_Schema):
    """Client-selected identifiers/time with all commercial inputs deliberately omitted."""

    branch_id: UUID
    service_id: UUID
    starts_at: datetime
    specialist_id: UUID | None = None


class HoldResponse(_Schema):
    """Database-backed reservation returned after a successful hold transaction."""

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

    @classmethod
    def from_result(cls, result: HoldResult) -> HoldResponse:
        """Translate an application result without ORM serialization."""

        return cls(**asdict(result))


class AvailabilityResponse(_Schema):
    """One client-visible available interval for one actual specialist."""

    specialist_id: UUID
    starts_at: datetime
    ends_at: datetime
    busy_starts_at: datetime
    busy_ends_at: datetime

    @classmethod
    def from_result(cls, result: AvailabilityResult) -> AvailabilityResponse:
        """Translate a pure slot result."""

        return cls(**asdict(result))


class CreateAppointmentRequest(_Schema):
    """Confirm a hold into a client-owned appointment."""

    hold_id: UUID
    customer_note: str | None = Field(default=None, max_length=5_000)


class CancelAppointmentRequest(_Schema):
    """Client cancellation input; staff/admin reason rules are enforced in the use case."""

    reason: str | None = Field(default=None, max_length=500)


class RescheduleCommitRequest(_Schema):
    """Commit a previously created replacement hold."""

    hold_id: UUID


class StatusTransitionRequest(_Schema):
    """Staff/admin transition input with no trusted appointment scope information."""

    target_status: AppointmentStatus
    reason: str | None = Field(default=None, max_length=500)


class AppointmentResponse(_Schema):
    """Frozen appointment snapshot plus computed payment state."""

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
    payment_status: str | None = None
    paid_amount: Decimal | None = None
    refundable_amount: Decimal | None = None
    requires_manual_refund: bool | None = None

    @classmethod
    def from_result(
        cls,
        result: AppointmentResult,
        *,
        actor: BookingActor,
    ) -> AppointmentResponse:
        """Map output while withholding payment details from non-financial staff roles."""

        values = asdict(result)
        if not _can_view_appointment_finance(actor):
            for field in (
                "payment_status",
                "paid_amount",
                "refundable_amount",
                "requires_manual_refund",
            ):
                values[field] = None
        return cls(**values)


def _can_view_appointment_finance(actor: BookingActor) -> bool:
    """Keep booking payment balances out of non-financial staff responses."""

    return actor.is_client or any(
        actor.has(permission)
        for permission in (
            PermissionCode.CASH_PAYMENTS_VIEW,
            PermissionCode.CASH_LEDGER_VIEW,
            PermissionCode.ANALYTICS_FINANCE_VIEW,
        )
    )


class CashShiftRequest(_Schema):
    """Open/close cash shift transport input."""

    cashbox_id: UUID
    amount: Decimal = Field(max_digits=14, decimal_places=2, ge=0)
    notes: str | None = Field(default=None, max_length=500)


class CashShiftResponse(_Schema):
    """Safe shift summary."""

    id: UUID
    cashbox_id: UUID
    status: str
    opening_amount: Decimal
    expected_closing_amount: Decimal | None
    actual_closing_amount: Decimal | None
    difference: Decimal | None

    @classmethod
    def from_result(cls, result: CashShiftResult) -> CashShiftResponse:
        """Map a shift result."""

        return cls(**asdict(result))


class PaymentRequest(_Schema):
    """Immutable payment input with an optional cashbox only for cash method."""

    appointment_id: UUID
    amount: Decimal = Field(max_digits=14, decimal_places=2, gt=0)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    method: PaymentMethod
    cashbox_id: UUID | None = None
    external_reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class RefundRequest(_Schema):
    """Immutable refund transport input."""

    payment_id: UUID
    amount: Decimal = Field(max_digits=14, decimal_places=2, gt=0)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    reason: str = Field(min_length=1, max_length=500)
    cashbox_id: UUID | None = None


class PaymentResponse(_Schema):
    """Payment/refund result including recomputed appointment balance."""

    id: UUID
    appointment_id: UUID
    amount: Decimal
    currency: str
    payment_status: str
    paid_amount: Decimal
    refundable_amount: Decimal

    @classmethod
    def from_result(cls, result: PaymentResult) -> PaymentResponse:
        """Map a payment aggregate result."""

        return cls(**asdict(result))


class CashTransactionRequest(_Schema):
    """Manual immutable cash delta."""

    cashbox_id: UUID
    type: CashTransactionType
    amount_delta: Decimal = Field(max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    reason: str = Field(min_length=1, max_length=500)


class StockMovementLineRequest(_Schema):
    """Manual inventory delta line."""

    product_id: UUID
    quantity_delta: Decimal = Field(max_digits=16, decimal_places=3)
    unit_cost: Decimal | None = Field(default=None, max_digits=14, decimal_places=2, ge=0)


class StockMovementRequest(_Schema):
    """Manual immutable receipt/write-off/adjustment input."""

    warehouse_id: UUID
    type: StockMovementType
    lines: list[StockMovementLineRequest] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: UUID | None = None


class StockMovementResponse(_Schema):
    """Movement header result after transactional balance writes."""

    id: UUID
    warehouse_id: UUID
    type: StockMovementType
    line_count: int

    @classmethod
    def from_result(cls, result: StockMovementResult) -> StockMovementResponse:
        """Map a movement result."""

        return cls(**asdict(result))


class AnalyticsRequestQuery(_Schema):
    """Bounded analytics filter represented in the OpenAPI schema."""

    date_from: date
    date_to: date
    timezone: str = Field(min_length=1, max_length=64)
    branch_id: UUID | None = None
    specialist_id: UUID | None = None
    service_id: UUID | None = None


class CustomerResponse(_Schema):
    """A customer profile safe for its owner and authorized booking staff."""

    id: UUID
    first_name: str
    last_name: str | None
    phone: str | None
    locale: str
    timezone: str | None
    is_blocked: bool


class BranchResponse(_Schema):
    """One organization branch visible to a booking client."""

    id: UUID
    name: str
    address: str | None
    timezone: str | None
    phone: str | None
    is_active: bool


class CategoryResponse(_Schema):
    """A tenant-owned optional service category."""

    id: UUID
    name: str
    sort_order: int
    is_active: bool


class ServiceResponse(_Schema):
    """A customer-visible service definition with server-owned commercial fields."""

    id: UUID
    category_id: UUID | None
    name: str
    description: str | None
    duration_minutes: int
    price: Decimal
    currency: str
    buffer_before_minutes: int
    buffer_after_minutes: int
    is_active: bool
    booking_enabled: bool
    sort_order: int


class SpecialistResponse(_Schema):
    """A customer-visible specialist selection card."""

    id: UUID
    display_name: str
    description: str | None
    is_active: bool
    accepts_bookings: bool


class ClientSettingsResponse(_Schema):
    """Only display and input behavior settings needed by a client application."""

    currency: str
    default_locale: str
    slot_step_minutes: int
    require_client_phone: bool


class ClientFeatureFlagsResponse(_Schema):
    """Explicit supported booking client capabilities rather than implicit UI guesses."""

    reschedule: bool
    client_cancellation: bool
    payments: bool


class ClientBootstrapResponse(_Schema):
    """Single bootstrap payload for a future client Telegram Mini App."""

    customer: CustomerResponse
    settings: ClientSettingsResponse
    organization_timezone: str
    available_locales: list[str]
    branches: list[BranchResponse]
    feature_flags: ClientFeatureFlagsResponse


class AppointmentListResponse(_Schema):
    """Offset pagination payload with deterministic page size and a no-total continuation hint."""

    items: list[AppointmentResponse]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)


class AdminResourcePayload(_Schema):
    """Whitelisted fields are enforced by the application resource contract per URL resource."""

    values: dict[str, Any]


class AdminResourceResponse(_Schema):
    """One explicitly mapped admin resource; it never contains a tenant identifier from input."""

    data: dict[str, Any]


class AdminResourceListResponse(_Schema):
    """Bounded generic CRUD page for documented admin resource routes."""

    items: list[dict[str, Any]]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    next_offset: int | None = Field(default=None, ge=0)


class AdminArchiveRequest(_Schema):
    """Optional audit rationale for archive/deactivation operations."""

    reason: str | None = Field(default=None, max_length=500)


class StaffBindCodeRequest(_Schema):
    """Bounded TTL request for a secure staff Telegram binding code."""

    specialist_id: UUID
    ttl_seconds: int = Field(default=900, ge=60, le=86_400)


class StaffBindCodeResponse(_Schema):
    """The raw code is returned only once to an authorized administrator."""

    code: str
    expires_at: datetime
    specialist_id: UUID


class AdminHoldRequest(HoldRequest):
    """Admin-only hold creation whose target customer must already belong to the tenant."""

    customer_id: UUID


class PriceOverrideRequest(_Schema):
    """Explicit reason is mandatory when changing a historical appointment snapshot price."""

    price: Decimal = Field(max_digits=14, decimal_places=2, ge=0)
    reason: str = Field(min_length=1, max_length=500)


class AnalyticsResponse(_Schema):
    """Database-aggregated dashboard output with a documented stable JSON envelope."""

    data: dict[str, Any]


class AccessRoleAssignmentRequest(_Schema):
    """One server-validated role assignment scope for the access-management API."""

    role_id: UUID
    scope: AccessScope
    branch_ids: list[UUID] = Field(default_factory=lambda: list[UUID](), max_length=100)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class AccessCreateMemberRequest(_Schema):
    """Create one staff membership and its initial scoped role assignments."""

    subject_id: UUID
    specialist_id: UUID | None = None
    display_name: str | None = Field(default=None, max_length=200)
    assignments: list[AccessRoleAssignmentRequest] = Field(min_length=1, max_length=20)


class AccessCustomRoleRequest(_Schema):
    """Tenant custom role input; codes are later checked against the central registry."""

    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5_000)
    permission_codes: list[str] = Field(min_length=1, max_length=100)


class AccessCustomRolePatchRequest(_Schema):
    """Optional custom-role updates; built-in roles are rejected by the service."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5_000)
    permission_codes: list[str] | None = Field(default=None, min_length=1, max_length=100)


class AccessCustomRoleCloneRequest(_Schema):
    """Naming input for a safe clone of a built-in or tenant custom role."""

    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5_000)


class AccessOwnershipTransferRequest(_Schema):
    """Target of an atomic tenant-OWNER transfer; callers never choose a role ID."""

    membership_id: UUID
    reason: str | None = Field(default=None, max_length=500)


class AccessReasonRequest(_Schema):
    """Bounded reason captured in sensitive revocation/deactivation audit events."""

    reason: str | None = Field(default=None, max_length=500)


class AccessDataResponse(_Schema):
    """Flexible but typed JSON envelope for normalized access-management representations."""

    data: dict[str, Any]


class AccessListResponse(_Schema):
    """List envelope for permissions, roles, members, and audit entries."""

    items: list[dict[str, Any]]
