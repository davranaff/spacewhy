"""Tenant-scoped SQLAlchemy models and PostgreSQL constraints for booking."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.core.db.base import Base
from app.modules.booking.domain.enums import (
    AccessRole,
    AccessScope,
    ActorType,
    AppointmentSource,
    AppointmentStatus,
    AuditSource,
    AvailabilityExceptionType,
    CashShiftStatus,
    CashTransactionType,
    ConversationState,
    OutboxStatus,
    PaymentMethod,
    ReservationStatus,
    ReservationType,
    StockMovementType,
)

_UUID = sa.Uuid(as_uuid=True)
_UTC_DATETIME = sa.DateTime(timezone=True)
_MONEY = sa.Numeric(14, 2)
_QUANTITY = sa.Numeric(16, 3)


def _uuid() -> UUID:
    """Generate a UUID only for new ORM instances."""

    return uuid4()


def _enum_values(members: type[StrEnum]) -> list[str]:
    """Return durable enum values accepted by the SQLAlchemy enum adapter."""

    return [member.value for member in members]


def _enum(enum_type: type[StrEnum], *, length: int) -> sa.Enum:
    """Persist public enum values, never Python member names."""

    return sa.Enum(
        enum_type,
        native_enum=False,
        length=length,
        values_callable=_enum_values,
    )


class TimestampMixin:
    """Server-timestamp fields shared by mutable booking rows."""

    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )


class BookingOrganization(TimestampMixin, Base):
    """Tenant root owned by the booking module until a shared tenant exists."""

    __tablename__ = "booking_organizations"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(sa.String(63), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    default_timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)


class BookingSettings(TimestampMixin, Base):
    """Organization-owned configuration rather than hard-coded booking policy."""

    __tablename__ = "booking_settings"

    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False, default="UZS")
    slot_step_minutes: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=15)
    min_booking_lead_minutes: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    max_booking_horizon_days: Mapped[int] = mapped_column(
        sa.SmallInteger, nullable=False, default=60
    )
    hold_ttl_seconds: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=300)
    client_cancellation_cutoff_minutes: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=120,
    )
    auto_confirm_booking: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    require_client_phone: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    prevent_customer_overlapping_appointments: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
    )
    max_upcoming_appointments_per_customer: Mapped[int] = mapped_column(
        sa.SmallInteger,
        nullable=False,
        default=5,
    )
    reminder_offsets_minutes: Mapped[list[int]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: [1440, 120],
    )
    daily_staff_agenda_time: Mapped[time] = mapped_column(
        sa.Time,
        nullable=False,
        default=time(18, 0),
    )
    allow_negative_stock: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    require_open_cash_shift_for_cash_payment: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
    )
    default_locale: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="ru")

    __table_args__ = (
        sa.CheckConstraint(
            "slot_step_minutes > 0",
            name="booking_settings_slot_step_positive",
        ),
        sa.CheckConstraint(
            "min_booking_lead_minutes >= 0",
            name="booking_settings_lead_non_negative",
        ),
        sa.CheckConstraint(
            "max_booking_horizon_days >= 0",
            name="booking_settings_horizon_non_negative",
        ),
        sa.CheckConstraint(
            "hold_ttl_seconds > 0",
            name="booking_settings_hold_ttl_positive",
        ),
        sa.CheckConstraint(
            "max_upcoming_appointments_per_customer > 0",
            name="booking_settings_upcoming_limit_positive",
        ),
    )


class BookingTelegramBotInstallation(TimestampMixin, Base):
    """One configured Telegram booking bot maps server-side to exactly one tenant."""

    __tablename__ = "booking_telegram_bot_installations"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.Index(
            "ix_booking_telegram_bot_installations_organization_active",
            "organization_id",
            "is_active",
        ),
    )


class BookingRateLimitBucket(TimestampMixin, Base):
    """Durable hashed-key rate-limit bucket shared safely across API worker processes."""

    __tablename__ = "booking_rate_limit_buckets"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    scope: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    key_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    request_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    __table_args__ = (
        sa.UniqueConstraint(
            "scope",
            "key_digest",
            name="booking_rate_limit_buckets_scope_key",
        ),
        sa.CheckConstraint(
            "request_count >= 0",
            name=conv("ck_booking_rate_limit_buckets_booking_rate_limit_buckets_count_"),
        ),
        sa.Index("ix_booking_rate_limit_buckets_window", "scope", "window_started_at"),
    )


class BookingAccessGrant(TimestampMixin, Base):
    """Persisted role and permission grant used by signed booking sessions."""

    __tablename__ = "booking_access_grants"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    role: Mapped[AccessRole] = mapped_column(
        _enum(AccessRole, length=32),
        nullable=False,
    )
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    customer_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    specialist_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "subject_id",
            name="booking_access_grants_organization_subject",
        ),
        sa.Index(
            "ix_booking_access_grants_organization_active",
            "organization_id",
            "is_active",
        ),
    )


class BookingPermissionDefinition(TimestampMixin, Base):
    """Globally owned, stable permission metadata; tenant users cannot invent codes."""

    __tablename__ = "booking_permission_definitions"

    code: Mapped[str] = mapped_column(sa.String(120), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    allowed_scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_sensitive: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.Index("ix_booking_permission_definitions_category", "category", "is_active"),
    )


class BookingRole(TimestampMixin, Base):
    """Global system role or organization-local custom role definition."""

    __tablename__ = "booking_roles"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    updated_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "code",
            name="booking_roles_organization_code",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "(is_system AND organization_id IS NULL) OR NOT is_system",
            name="booking_roles_system_global",
        ),
        sa.Index("ix_booking_roles_organization_active", "organization_id", "is_active"),
    )


class BookingRolePermission(Base):
    """Normalized role-to-registry permission mapping."""

    __tablename__ = "booking_role_permissions"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    role_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_code: Mapped[str] = mapped_column(
        sa.String(120),
        sa.ForeignKey("booking_permission_definitions.code", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint("role_id", "permission_code", name="booking_role_permissions_scope"),
        sa.Index("ix_booking_role_permissions_permission", "permission_code", "role_id"),
    )


class BookingMembership(TimestampMixin, Base):
    """A tenant membership for a staff subject; clients intentionally do not receive one."""

    __tablename__ = "booking_memberships"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    specialist_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="SET NULL"),
        nullable=True,
    )
    display_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    access_version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    deactivated_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    deactivated_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    deactivation_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "subject_id",
            name="booking_memberships_organization_subject",
        ),
        sa.CheckConstraint(
            "access_version > 0",
            name=conv("ck_booking_memberships_booking_memberships_access_versi_2574"),
        ),
        sa.Index("ix_booking_memberships_organization_active", "organization_id", "is_active"),
        sa.Index("ix_booking_memberships_specialist", "organization_id", "specialist_id"),
    )


class BookingRoleAssignment(TimestampMixin, Base):
    """One revocable role assignment with an explicit durable authorization scope."""

    __tablename__ = "booking_role_assignments"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scope: Mapped[AccessScope] = mapped_column(_enum(AccessScope, length=24), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    assigned_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="booking_role_assignments_window",
        ),
        sa.Index(
            "uq_booking_role_assignments_active_scope",
            "membership_id",
            "role_id",
            "scope",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
        sa.Index(
            "ix_booking_role_assignments_membership_active",
            "organization_id",
            "membership_id",
            "is_active",
        ),
    )


class BookingRoleAssignmentBranch(Base):
    """Branch list for a branch-scoped role assignment; no implicit all-branch fallback."""

    __tablename__ = "booking_role_assignment_branches"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    assignment_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_role_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "assignment_id",
            "branch_id",
            name="booking_role_assignment_branches_scope",
        ),
        sa.Index("ix_booking_role_assignment_branches_branch", "branch_id", "assignment_id"),
    )


class BookingPlatformAdministrator(TimestampMixin, Base):
    """Separate platform-internal authority, never derived from tenant OWNER membership."""

    __tablename__ = "booking_platform_administrators"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    subject_id: Mapped[UUID] = mapped_column(_UUID, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    access_version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    revoked_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "access_version > 0",
            name=conv("ck_booking_platform_administrators_booking_platform_adm_ab89"),
        ),
    )


class BookingBranch(TimestampMixin, Base):
    """Organization branch with optional timezone override."""

    __tablename__ = "booking_branches"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    address: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    timezone: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="booking_branches_organization_name",
        ),
        sa.Index("ix_booking_branches_organization_active", "organization_id", "is_active"),
    )


class ServiceCategory(TimestampMixin, Base):
    """Optional organization-owned service category."""

    __tablename__ = "booking_service_categories"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="booking_service_categories_organization_name",
        ),
    )


class BookingService(TimestampMixin, Base):
    """Bookable service template; historical appointments keep snapshots."""

    __tablename__ = "booking_services"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_service_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    default_duration_minutes: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    default_price: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=0)
    buffer_after_minutes: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    booking_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    archived_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "default_duration_minutes > 0",
            name="booking_services_duration_positive",
        ),
        sa.CheckConstraint("default_price >= 0", name="booking_services_price_non_negative"),
        sa.CheckConstraint(
            "buffer_before_minutes >= 0",
            name="booking_services_buffer_before_non_negative",
        ),
        sa.CheckConstraint(
            "buffer_after_minutes >= 0",
            name="booking_services_buffer_after_non_negative",
        ),
        sa.Index(
            "ix_booking_services_organization_active",
            "organization_id",
            "is_active",
            "booking_enabled",
        ),
    )


class Specialist(TimestampMixin, Base):
    """Employee or independent service provider within one organization."""

    __tablename__ = "booking_specialists"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    core_user_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    display_name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    accepts_bookings: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    archived_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)

    __table_args__ = (
        sa.Index(
            "ix_booking_specialists_organization_active",
            "organization_id",
            "is_active",
            "accepts_bookings",
        ),
    )


class SpecialistService(TimestampMixin, Base):
    """Tenant-scoped specialist capability with optional commercial overrides."""

    __tablename__ = "booking_specialist_services"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    custom_duration_minutes: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    custom_price: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    custom_buffer_before_minutes: Mapped[int | None] = mapped_column(
        sa.SmallInteger,
        nullable=True,
    )
    custom_buffer_after_minutes: Mapped[int | None] = mapped_column(
        sa.SmallInteger,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    booking_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "specialist_id",
            "service_id",
            "branch_id",
            name="booking_specialist_services_scope",
        ),
        sa.CheckConstraint(
            "custom_duration_minutes IS NULL OR custom_duration_minutes > 0",
            name=conv("ck_booking_specialist_services_booking_specialist_servi_28e8"),
        ),
        sa.CheckConstraint(
            "custom_price IS NULL OR custom_price >= 0",
            name=conv("ck_booking_specialist_services_booking_specialist_servi_9a5c"),
        ),
        sa.CheckConstraint(
            "custom_buffer_before_minutes IS NULL OR custom_buffer_before_minutes >= 0",
            name=conv("ck_booking_specialist_services_booking_specialist_servi_07d1"),
        ),
        sa.CheckConstraint(
            "custom_buffer_after_minutes IS NULL OR custom_buffer_after_minutes >= 0",
            name=conv("ck_booking_specialist_services_booking_specialist_servi_777b"),
        ),
        sa.Index(
            "ix_booking_specialist_services_lookup",
            "organization_id",
            "branch_id",
            "service_id",
            "is_active",
        ),
    )


class WorkingSchedule(TimestampMixin, Base):
    """One non-overnight local working interval; multiple per weekday are allowed."""

    __tablename__ = "booking_working_schedules"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    local_start_time: Mapped[time] = mapped_column(sa.Time, nullable=False)
    local_end_time: Mapped[time] = mapped_column(sa.Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="booking_schedule_weekday_range"),
        sa.CheckConstraint(
            "local_end_time > local_start_time",
            name="booking_schedule_same_day_interval",
        ),
        sa.Index(
            "ix_booking_working_schedules_scope",
            "organization_id",
            "specialist_id",
            "branch_id",
            "weekday",
        ),
        ExcludeConstraint(
            ("organization_id", "="),
            ("specialist_id", "="),
            ("branch_id", "="),
            ("weekday", "="),
            (
                sa.text(
                    "tsrange("
                    "(DATE '2000-01-03' + local_start_time), "
                    "(DATE '2000-01-03' + local_end_time), '[)')"
                ),
                "&&",
            ),
            where=sa.text("is_active"),
            using="gist",
            name="booking_working_schedules_no_active_overlap",
        ),
    )


class AvailabilityException(TimestampMixin, Base):
    """UTC override or unavailable interval for one specialist at one branch."""

    __tablename__ = "booking_availability_exceptions"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[AvailabilityExceptionType] = mapped_column(
        _enum(AvailabilityExceptionType, length=32),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.CheckConstraint(
            "ends_at > starts_at",
            name=conv("ck_booking_availability_exceptions_booking_availability_ebd5"),
        ),
        sa.Index(
            "ix_booking_availability_exceptions_lookup",
            "organization_id",
            "specialist_id",
            "branch_id",
            "starts_at",
        ),
    )


class Customer(TimestampMixin, Base):
    """Tenant-scoped customer; phone remains intentionally non-unique."""

    __tablename__ = "booking_customers"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    last_name: Mapped[str | None] = mapped_column(sa.String(160), nullable=True)
    normalized_phone: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    locale: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="ru")
    timezone: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    __table_args__ = (
        sa.Index("ix_booking_customers_organization_created", "organization_id", "created_at"),
        sa.Index(
            "ix_booking_customers_organization_phone",
            "organization_id",
            "normalized_phone",
        ),
    )


class CustomerIdentity(TimestampMixin, Base):
    """External provider identity unique only within organization and bot app."""

    __tablename__ = "booking_customer_identities"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    external_user_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    external_chat_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "provider",
            "bot_app_id",
            "external_user_id",
            name="booking_customer_identities_provider_user",
        ),
        sa.Index(
            "ix_booking_customer_identities_customer",
            "organization_id",
            "customer_id",
        ),
    )


class StaffTelegramBinding(TimestampMixin, Base):
    """Verified Telegram-to-membership association created from a one-time bind code."""

    __tablename__ = "booking_staff_telegram_bindings"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    bound_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)

    __table_args__ = (
        sa.Index(
            "uq_booking_staff_bindings_active_specialist",
            "organization_id",
            "specialist_id",
            "bot_app_id",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
        sa.Index(
            "uq_booking_staff_bindings_active_telegram",
            "organization_id",
            "bot_app_id",
            "telegram_user_id",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
        sa.Index(
            "ix_booking_staff_bindings_membership_active",
            "organization_id",
            "membership_id",
            "is_active",
        ),
    )


class StaffBindCode(TimestampMixin, Base):
    """One-time, hash-only staff binding code; raw code is never persisted."""

    __tablename__ = "booking_staff_bind_codes"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    code_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    revoked_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by: Mapped[UUID] = mapped_column(_UUID, nullable=False)

    __table_args__ = (
        sa.CheckConstraint("expires_at > created_at", name="booking_bind_codes_expiry"),
        sa.Index(
            "ix_booking_staff_bind_codes_lookup",
            "organization_id",
            "specialist_id",
            "expires_at",
        ),
    )


class SlotReservation(TimestampMixin, Base):
    """Database-backed hold or committed appointment busy interval."""

    __tablename__ = "booking_slot_reservations"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    service_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    busy_starts_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    busy_ends_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    type: Mapped[ReservationType] = mapped_column(
        _enum(ReservationType, length=16),
        nullable=False,
    )
    status: Mapped[ReservationStatus] = mapped_column(
        _enum(ReservationStatus, length=16),
        nullable=False,
        default=ReservationStatus.ACTIVE,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_appointments.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    owner_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "ends_at > starts_at",
            name=conv("ck_booking_slot_reservations_booking_reservations_servi_baae"),
        ),
        sa.CheckConstraint(
            "busy_ends_at > busy_starts_at",
            name="booking_reservations_busy_interval",
        ),
        sa.CheckConstraint(
            "busy_starts_at <= starts_at AND busy_ends_at >= ends_at",
            name=conv("ck_booking_slot_reservations_booking_reservations_busy__7d17"),
        ),
        sa.CheckConstraint(
            "(type = 'hold' AND expires_at IS NOT NULL) OR "
            "(type = 'appointment' AND expires_at IS NULL)",
            name=conv("ck_booking_slot_reservations_booking_reservations_expir_d40f"),
        ),
        ExcludeConstraint(
            ("organization_id", "="),
            ("specialist_id", "="),
            (sa.text("tstzrange(busy_starts_at, busy_ends_at, '[)')"), "&&"),
            where=sa.text("status = 'active'"),
            using="gist",
            name="booking_reservations_no_active_overlap",
        ),
        sa.Index(
            "ix_booking_reservations_specialist_busy",
            "organization_id",
            "specialist_id",
            "status",
            "busy_starts_at",
        ),
        sa.Index(
            "uq_booking_reservations_active_idempotency",
            "organization_id",
            "owner_key",
            "idempotency_key",
            unique=True,
            postgresql_where=sa.text(
                "idempotency_key IS NOT NULL AND status = 'active' AND type = 'hold'"
            ),
        ),
    )


class Appointment(TimestampMixin, Base):
    """Immutable commercial snapshots plus mutable lifecycle timestamps."""

    __tablename__ = "booking_appointments"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    public_number: Mapped[str] = mapped_column(sa.String(40), nullable=False, unique=True)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    specialist_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_specialists.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reservation_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_slot_reservations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        _enum(AppointmentStatus, length=16),
        nullable=False,
    )
    source: Mapped[AppointmentSource] = mapped_column(
        _enum(AppointmentSource, length=32),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    busy_starts_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    busy_ends_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    service_name_snapshot: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    specialist_name_snapshot: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    duration_minutes_snapshot: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    price_snapshot: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency_snapshot: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    customer_note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    internal_note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    cancelled_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    no_show_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)

    __table_args__ = (
        sa.CheckConstraint("ends_at > starts_at", name="booking_appointments_service_interval"),
        sa.CheckConstraint(
            "busy_ends_at > busy_starts_at",
            name="booking_appointments_busy_interval",
        ),
        sa.CheckConstraint("price_snapshot >= 0", name="booking_appointments_price_non_negative"),
        sa.CheckConstraint(
            "duration_minutes_snapshot > 0",
            name="booking_appointments_duration_positive",
        ),
        sa.CheckConstraint("version > 0", name="booking_appointments_version_positive"),
        sa.Index(
            "ix_booking_appointments_organization_status_start",
            "organization_id",
            "status",
            "starts_at",
        ),
        sa.Index(
            "ix_booking_appointments_customer_status_start",
            "organization_id",
            "customer_id",
            "status",
            "starts_at",
        ),
        sa.Index(
            "ix_booking_appointments_specialist_status_start",
            "organization_id",
            "specialist_id",
            "status",
            "starts_at",
        ),
    )


class AppointmentHistory(Base):
    """Append-only appointment changes and administrative override audit evidence."""

    __tablename__ = "booking_appointment_history"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    old_status: Mapped[AppointmentStatus | None] = mapped_column(
        _enum(AppointmentStatus, length=16),
        nullable=True,
    )
    new_status: Mapped[AppointmentStatus | None] = mapped_column(
        _enum(AppointmentStatus, length=16),
        nullable=True,
    )
    old_starts_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    new_starts_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    actor_type: Mapped[ActorType] = mapped_column(
        _enum(ActorType, length=16),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "ix_booking_appointment_history_appointment_created",
            "organization_id",
            "appointment_id",
            "created_at",
        ),
    )


class BookingIdempotencyRecord(TimestampMixin, Base):
    """Persistent replay result scoped by tenant, actor, operation, and supplied key."""

    __tablename__ = "booking_idempotency_records"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    operation: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "actor_id",
            "operation",
            "key",
            name="booking_idempotency_scope",
        ),
        sa.CheckConstraint(
            "response_status >= 200 AND response_status < 600",
            name=conv("ck_booking_idempotency_records_booking_idempotency_resp_145b"),
        ),
    )


class NotificationOutbox(TimestampMixin, Base):
    """Durable at-least-once notification intent created inside business transactions."""

    __tablename__ = "booking_notification_outbox"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_appointments.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    channel: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="telegram")
    recipient_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    recipient_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    chat_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    locale: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    template_key: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scheduled_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        _enum(OutboxStatus, length=16),
        nullable=False,
        default=OutboxStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=5)
    dedupe_key: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    last_error: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "dedupe_key",
            name="booking_notification_outbox_dedupe",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name=conv("ck_booking_notification_outbox_booking_outbox_attempts__8962"),
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name=conv("ck_booking_notification_outbox_booking_outbox_max_attem_56ad"),
        ),
        sa.Index(
            "ix_booking_notification_outbox_poll",
            "status",
            "scheduled_at",
            "created_at",
        ),
    )


class Cashbox(TimestampMixin, Base):
    """An internal physical or virtual cashbox per branch and currency."""

    __tablename__ = "booking_cashboxes"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "branch_id",
            "name",
            name="booking_cashboxes_scope_name",
        ),
        sa.Index("ix_booking_cashboxes_organization_branch", "organization_id", "branch_id"),
    )


class CashShift(TimestampMixin, Base):
    """One concurrently protected open shift per cashbox."""

    __tablename__ = "booking_cash_shifts"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    cashbox_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_cashboxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    opened_by: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    opening_amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    closed_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    expected_closing_amount: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    actual_closing_amount: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    status: Mapped[CashShiftStatus] = mapped_column(
        _enum(CashShiftStatus, length=16),
        nullable=False,
        default=CashShiftStatus.OPEN,
    )
    notes: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    __table_args__ = (
        sa.CheckConstraint("opening_amount >= 0", name="booking_cash_shifts_opening_non_negative"),
        sa.Index(
            "uq_booking_cash_shifts_one_open",
            "cashbox_id",
            unique=True,
            postgresql_where=sa.text("status = 'open'"),
        ),
        sa.Index(
            "ix_booking_cash_shifts_organization_status",
            "organization_id",
            "status",
            "opened_at",
        ),
    )


class Payment(Base):
    """Immutable appointment payment; amount cannot exceed outstanding in the use case."""

    __tablename__ = "booking_payments"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_appointments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        _enum(PaymentMethod, length=16),
        nullable=False,
    )
    cash_shift_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_cash_shifts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    __table_args__ = (
        sa.CheckConstraint("amount > 0", name="booking_payments_amount_positive"),
        sa.UniqueConstraint(
            "organization_id",
            "created_by",
            "idempotency_key",
            name="booking_payments_idempotency",
        ),
        sa.Index(
            "ix_booking_payments_appointment_created",
            "organization_id",
            "appointment_id",
            "created_at",
        ),
    )


class Refund(Base):
    """Immutable refund associated with one immutable original payment."""

    __tablename__ = "booking_refunds"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    cash_shift_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_cash_shifts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)

    __table_args__ = (
        sa.CheckConstraint("amount > 0", name="booking_refunds_amount_positive"),
        sa.UniqueConstraint(
            "organization_id",
            "created_by",
            "idempotency_key",
            name="booking_refunds_idempotency",
        ),
        sa.Index("ix_booking_refunds_payment_created", "payment_id", "created_at"),
    )


class CashTransaction(Base):
    """Append-only cash ledger, including reversals rather than mutable correction."""

    __tablename__ = "booking_cash_transactions"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cashbox_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_cashboxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cash_shift_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_cash_shifts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    type: Mapped[CashTransactionType] = mapped_column(
        _enum(CashTransactionType, length=32),
        nullable=False,
    )
    amount_delta: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "uq_booking_cash_transactions_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        ),
        sa.Index("ix_booking_cash_transactions_cashbox_created", "cashbox_id", "created_at"),
    )


class Warehouse(TimestampMixin, Base):
    """Simple branch warehouse; procurement and lot tracking remain outside v1."""

    __tablename__ = "booking_warehouses"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "branch_id",
            "name",
            name="booking_warehouses_scope_name",
        ),
        sa.Index(
            "uq_booking_warehouses_default_branch",
            "branch_id",
            unique=True,
            postgresql_where=sa.text("is_default AND is_active"),
        ),
    )


class Product(TimestampMixin, Base):
    """Inventory product measured in a declared business unit."""

    __tablename__ = "booking_products"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    sku: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    unit: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    low_stock_threshold: Mapped[Decimal | None] = mapped_column(_QUANTITY, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    track_stock: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.Index(
            "uq_booking_products_organization_sku",
            "organization_id",
            "sku",
            unique=True,
            postgresql_where=sa.text("sku IS NOT NULL"),
        ),
        sa.CheckConstraint(
            "low_stock_threshold IS NULL OR low_stock_threshold >= 0",
            name="booking_products_low_stock_non_negative",
        ),
        sa.Index("ix_booking_products_organization_active", "organization_id", "is_active"),
    )


class StockBalance(TimestampMixin, Base):
    """One locked balance row per warehouse/product pair."""

    __tablename__ = "booking_stock_balances"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(_QUANTITY, nullable=False, default=Decimal("0"))
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)

    __table_args__ = (
        sa.UniqueConstraint("warehouse_id", "product_id", name="booking_stock_balances_scope"),
        sa.CheckConstraint(
            "version > 0",
            name=conv("ck_booking_stock_balances_booking_stock_balances_versio_6824"),
        ),
        sa.Index("ix_booking_stock_balances_product", "organization_id", "product_id"),
    )


class StockMovement(Base):
    """Immutable stock movement header."""

    __tablename__ = "booking_stock_movements"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[StockMovementType] = mapped_column(
        _enum(StockMovementType, length=32),
        nullable=False,
    )
    reference_type: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "uq_booking_stock_movements_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        ),
        sa.Index(
            "ix_booking_stock_movements_warehouse_created",
            "warehouse_id",
            "created_at",
        ),
    )


class StockMovementItem(Base):
    """Immutable quantity delta line associated with one movement."""

    __tablename__ = "booking_stock_movement_items"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_stock_movements.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity_delta: Mapped[Decimal] = mapped_column(_QUANTITY, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "quantity_delta <> 0",
            name=conv("ck_booking_stock_movement_items_booking_stock_movement__9ac8"),
        ),
        sa.CheckConstraint(
            "unit_cost IS NULL OR unit_cost >= 0",
            name=conv("ck_booking_stock_movement_items_booking_stock_movement__7a66"),
        ),
        sa.Index(
            "ix_booking_stock_movement_items_product",
            "organization_id",
            "product_id",
        ),
    )


class ServiceMaterial(TimestampMixin, Base):
    """Active service recipe row copied into appointment snapshots at booking time."""

    __tablename__ = "booking_service_materials"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_services.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_warehouses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quantity_required: Mapped[Decimal] = mapped_column(_QUANTITY, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "service_id",
            "product_id",
            "warehouse_id",
            name="booking_service_materials_scope",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "quantity_required > 0",
            name=conv("ck_booking_service_materials_booking_service_materials__8ce6"),
        ),
    )


class AppointmentMaterialSnapshot(Base):
    """Recipe frozen at booking confirmation so later recipe edits cannot alter history."""

    __tablename__ = "booking_appointment_material_snapshots"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_appointments.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_warehouses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quantity_required: Mapped[Decimal] = mapped_column(_QUANTITY, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "appointment_id",
            "product_id",
            "warehouse_id",
            name="booking_appointment_material_snapshots_scope",
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint(
            "quantity_required > 0",
            name=conv("ck_booking_appointment_material_snapshots_booking_appoi_902c"),
        ),
    )


class TelegramUpdateReceipt(Base):
    """Idempotency receipt for a provider update before a bot side effect is applied."""

    __tablename__ = "booking_telegram_update_receipts"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    provider_update_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "bot_app_id",
            "provider_update_id",
            name="booking_telegram_update_receipts_scope",
        ),
        sa.Index(
            "ix_booking_telegram_update_receipts_processed",
            "organization_id",
            "processed_at",
        ),
    )


class BookingConversation(TimestampMixin, Base):
    """Server-side bot FSM state; callback payloads contain only signed references."""

    __tablename__ = "booking_conversations"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    state: Mapped[ConversationState] = mapped_column(
        _enum(ConversationState, length=32),
        nullable=False,
        default=ConversationState.IDLE,
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    callback_nonce: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="")
    expires_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)

    __table_args__ = (
        sa.UniqueConstraint(
            "organization_id",
            "bot_app_id",
            "telegram_user_id",
            "telegram_chat_id",
            name="booking_conversations_scope",
        ),
        sa.CheckConstraint(
            "version > 0",
            name="booking_conversations_version_positive",
        ),
        sa.Index(
            "ix_booking_conversations_expiry",
            "organization_id",
            "expires_at",
        ),
    )


class BookingAuditLog(Base):
    """Append-only tenant audit log for security-sensitive booking operations."""

    __tablename__ = "booking_audit_log"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_branches.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    action_code: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(
        _enum(ActorType, length=16),
        nullable=False,
    )
    actor_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    actor_membership_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("booking_memberships.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[AuditSource] = mapped_column(
        _enum(AuditSource, length=24),
        nullable=False,
        default=AuditSource.API,
    )
    target_type: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    request_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    task_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME,
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.Index(
            "ix_booking_audit_log_organization_created",
            "organization_id",
            "created_at",
        ),
        sa.Index(
            "ix_booking_audit_log_target",
            "organization_id",
            "target_type",
            "target_id",
        ),
        sa.Index(
            "ix_booking_audit_log_action_created",
            "organization_id",
            "action_code",
            "created_at",
        ),
    )
