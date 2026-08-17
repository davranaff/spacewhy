"""Back-office booking resource management with explicit fields and tenant checks."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, cast
from uuid import UUID
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
from app.modules.booking.application.permissions import BookingPermission, PermissionCode
from app.modules.booking.domain.enums import AccessRole, ActorType, AvailabilityExceptionType
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.domain.value_objects import require_aware
from app.modules.booking.infrastructure.persistence.models import (
    AvailabilityException,
    BookingBranch,
    BookingMembership,
    BookingSettings,
    BookingTelegramBotInstallation,
    Cashbox,
    Customer,
    Product,
    ServiceCategory,
    ServiceMaterial,
    Specialist,
    SpecialistService,
    StaffBindCode,
    StaffTelegramBinding,
    Warehouse,
    WorkingSchedule,
)
from app.modules.booking.infrastructure.persistence.models import (
    BookingService as BookingServiceModel,
)


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """The explicit mutable field contract for one admin-managed aggregate."""

    model: type[Any]
    permission: PermissionCode | BookingPermission
    fields: tuple[str, ...]
    required_fields: frozenset[str]
    active_field: str | None = "is_active"
    archived_field: str | None = None
    branch_field: str | None = None
    manage_permission: PermissionCode | BookingPermission | None = None
    create_permission: PermissionCode | BookingPermission | None = None
    archive_permission: PermissionCode | BookingPermission | None = None


_RESOURCE_SPECS: dict[str, ResourceSpec] = {
    "branches": ResourceSpec(
        model=BookingBranch,
        permission=PermissionCode.BRANCHES_VIEW,
        fields=("name", "address", "timezone", "phone", "is_active"),
        required_fields=frozenset({"name"}),
        branch_field="id",
        manage_permission=PermissionCode.BRANCHES_UPDATE,
        create_permission=PermissionCode.BRANCHES_CREATE,
        archive_permission=PermissionCode.BRANCHES_DELETE,
    ),
    "categories": ResourceSpec(
        model=ServiceCategory,
        permission=PermissionCode.CATEGORIES_VIEW,
        fields=("name", "sort_order", "is_active"),
        required_fields=frozenset({"name"}),
        manage_permission=PermissionCode.CATEGORIES_MANAGE,
    ),
    "services": ResourceSpec(
        model=BookingServiceModel,
        permission=PermissionCode.SERVICES_VIEW,
        fields=(
            "category_id",
            "name",
            "description",
            "default_duration_minutes",
            "default_price",
            "currency",
            "buffer_before_minutes",
            "buffer_after_minutes",
            "is_active",
            "booking_enabled",
            "sort_order",
        ),
        required_fields=frozenset(
            {"name", "default_duration_minutes", "default_price", "currency"}
        ),
        archived_field="archived_at",
        manage_permission=PermissionCode.SERVICES_MANAGE,
    ),
    "specialists": ResourceSpec(
        model=Specialist,
        permission=PermissionCode.STAFF_VIEW,
        fields=(
            "core_user_id",
            "display_name",
            "description",
            "phone",
            "is_active",
            "accepts_bookings",
        ),
        required_fields=frozenset({"display_name"}),
        archived_field="archived_at",
        manage_permission=PermissionCode.STAFF_MANAGE,
    ),
    "specialist-services": ResourceSpec(
        model=SpecialistService,
        permission=PermissionCode.STAFF_VIEW,
        fields=(
            "specialist_id",
            "service_id",
            "branch_id",
            "custom_duration_minutes",
            "custom_price",
            "custom_buffer_before_minutes",
            "custom_buffer_after_minutes",
            "is_active",
            "booking_enabled",
        ),
        required_fields=frozenset({"specialist_id", "service_id", "branch_id"}),
        branch_field="branch_id",
        manage_permission=PermissionCode.STAFF_MANAGE,
    ),
    "schedules": ResourceSpec(
        model=WorkingSchedule,
        permission=PermissionCode.AVAILABILITY_VIEW,
        fields=(
            "specialist_id",
            "branch_id",
            "weekday",
            "local_start_time",
            "local_end_time",
            "is_active",
        ),
        required_fields=frozenset(
            {"specialist_id", "branch_id", "weekday", "local_start_time", "local_end_time"}
        ),
        branch_field="branch_id",
        manage_permission=PermissionCode.AVAILABILITY_MANAGE,
    ),
    "availability-exceptions": ResourceSpec(
        model=AvailabilityException,
        permission=PermissionCode.AVAILABILITY_VIEW,
        fields=(
            "specialist_id",
            "branch_id",
            "type",
            "starts_at",
            "ends_at",
            "reason",
            "is_active",
        ),
        required_fields=frozenset({"specialist_id", "branch_id", "type", "starts_at", "ends_at"}),
        branch_field="branch_id",
        manage_permission=PermissionCode.AVAILABILITY_EXCEPTIONS_MANAGE,
    ),
    "customers": ResourceSpec(
        model=Customer,
        permission=PermissionCode.CLIENTS_VIEW,
        fields=(
            "first_name",
            "last_name",
            "normalized_phone",
            "locale",
            "timezone",
            "notes",
            "is_blocked",
        ),
        required_fields=frozenset({"first_name"}),
        active_field=None,
        manage_permission=PermissionCode.CLIENTS_UPDATE,
        create_permission=PermissionCode.CLIENTS_CREATE,
    ),
    "cashboxes": ResourceSpec(
        model=Cashbox,
        permission=PermissionCode.ORGANIZATION_SETTINGS_MANAGE,
        fields=("branch_id", "name", "currency", "is_active"),
        required_fields=frozenset({"branch_id", "name", "currency"}),
        branch_field="branch_id",
    ),
    "products": ResourceSpec(
        model=Product,
        permission=PermissionCode.INVENTORY_PRODUCTS_VIEW,
        fields=(
            "name",
            "sku",
            "unit",
            "low_stock_threshold",
            "is_active",
            "track_stock",
        ),
        required_fields=frozenset({"name", "unit"}),
        manage_permission=PermissionCode.INVENTORY_PRODUCTS_MANAGE,
    ),
    "warehouses": ResourceSpec(
        model=Warehouse,
        permission=PermissionCode.INVENTORY_STOCK_VIEW,
        fields=("branch_id", "name", "is_default", "is_active"),
        required_fields=frozenset({"branch_id", "name"}),
        branch_field="branch_id",
        manage_permission=PermissionCode.INVENTORY_PRODUCTS_MANAGE,
    ),
    "service-materials": ResourceSpec(
        model=ServiceMaterial,
        permission=PermissionCode.INVENTORY_PRODUCTS_VIEW,
        fields=("service_id", "product_id", "warehouse_id", "quantity_required", "is_active"),
        required_fields=frozenset({"service_id", "product_id", "quantity_required"}),
        manage_permission=PermissionCode.INVENTORY_PRODUCTS_MANAGE,
    ),
}

_FOREIGN_MODELS: dict[str, type[Any]] = {
    "branch_id": BookingBranch,
    "category_id": ServiceCategory,
    "specialist_id": Specialist,
    "service_id": BookingServiceModel,
    "customer_id": Customer,
    "cashbox_id": Cashbox,
    "warehouse_id": Warehouse,
    "product_id": Product,
}


class BookingManagementService:
    """Tenant-safe admin CRUD and binding workflows without generic mass assignment."""

    def __init__(self, *, database: Database, clock: Clock | None = None) -> None:
        """Construct application behavior with scoped infrastructure only."""

        self._database = database
        self._clock = clock or SystemClock()

    async def list_resources(
        self,
        *,
        actor: BookingActor,
        resource: str,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[dict[str, Any], ...]:
        """List a bounded resource collection, always filtered by the signed organization."""

        spec = _resource_spec(resource)
        actor.require(spec.permission)
        if limit < 1 or limit > 100 or offset < 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        async with self._database.session() as session:
            statement = sa.select(spec.model).where(
                spec.model.organization_id == actor.organization_id
            )
            statement = _scoped_resource_statement(
                actor=actor,
                spec=spec,
                permission=spec.permission,
                statement=statement,
            )
            if not include_inactive:
                if spec.active_field is not None:
                    statement = statement.where(getattr(spec.model, spec.active_field).is_(True))
                if spec.archived_field is not None:
                    statement = statement.where(getattr(spec.model, spec.archived_field).is_(None))
            rows = (
                await session.scalars(
                    statement.order_by(spec.model.created_at.desc(), spec.model.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
            return tuple(_resource_view(spec, row, actor=actor) for row in rows)

    async def get_resource(
        self,
        *,
        actor: BookingActor,
        resource: str,
        resource_id: UUID,
    ) -> dict[str, Any]:
        """Load one resource through both its opaque ID and verified tenant scope."""

        spec = _resource_spec(resource)
        actor.require(spec.permission)
        async with self._database.session() as session:
            entity = await _resource_for_update(
                session,
                spec=spec,
                organization_id=actor.organization_id,
                resource_id=resource_id,
                lock=False,
            )
            _require_resource_scope(
                actor=actor,
                spec=spec,
                permission=spec.permission,
                entity=entity,
            )
            return _resource_view(spec, entity, actor=actor)

    async def create_resource(
        self,
        *,
        actor: BookingActor,
        resource: str,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Create one explicit whitelisted resource and an audit entry in one transaction."""

        spec = _resource_spec(resource)
        permission = _operation_permission(spec, operation="create")
        actor.require(permission)
        normalized = _normalize_resource_values(spec, values, creating=True)
        _require_resource_field_permissions(actor=actor, resource=resource, values=normalized)
        _require_resource_create_scope(
            actor=actor,
            spec=spec,
            permission=permission,
            values=normalized,
        )
        async with self._database.session() as session, session.begin():
            await _validate_references(
                session,
                organization_id=actor.organization_id,
                values=normalized,
            )
            if resource == "schedules":
                await _validate_schedule_interval(
                    session,
                    organization_id=actor.organization_id,
                    values=normalized,
                )
            entity = spec.model(organization_id=actor.organization_id, **normalized)
            if resource == "availability-exceptions":
                entity.created_by = actor.subject_id
            session.add(entity)
            try:
                await session.flush()
            except IntegrityError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            _audit(
                session,
                actor=actor,
                event_type=f"{resource}.created",
                target_type=resource,
                target_id=entity.id,
                branch_id=_resource_branch_id(spec, entity),
                after=_price_audit_value(resource=resource, values=normalized),
            )
            return _resource_view(spec, entity, actor=actor)

    async def update_resource(
        self,
        *,
        actor: BookingActor,
        resource: str,
        resource_id: UUID,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Update only named writable fields while retaining historical entity identity."""

        spec = _resource_spec(resource)
        permission = _operation_permission(spec, operation="update")
        actor.require(permission)
        normalized = _normalize_resource_values(spec, values, creating=False)
        if not normalized:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        _require_resource_field_permissions(actor=actor, resource=resource, values=normalized)
        async with self._database.session() as session, session.begin():
            entity = await _resource_for_update(
                session,
                spec=spec,
                organization_id=actor.organization_id,
                resource_id=resource_id,
                lock=True,
            )
            _require_resource_scope(actor=actor, spec=spec, permission=permission, entity=entity)
            before_price = _price_audit_value(
                resource=resource,
                values={field: getattr(entity, field) for field in normalized},
            )
            if spec.branch_field is not None and spec.branch_field in normalized:
                _require_resource_create_scope(
                    actor=actor,
                    spec=spec,
                    permission=permission,
                    values=normalized,
                )
            await _validate_references(
                session,
                organization_id=actor.organization_id,
                values=normalized,
            )
            if resource == "schedules":
                schedule_values = {
                    field: normalized.get(field, getattr(entity, field)) for field in spec.fields
                }
                await _validate_schedule_interval(
                    session,
                    organization_id=actor.organization_id,
                    values=schedule_values,
                    excluding_id=entity.id,
                )
            for field, value in normalized.items():
                setattr(entity, field, value)
            try:
                await session.flush()
            except IntegrityError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            _audit(
                session,
                actor=actor,
                event_type=f"{resource}.updated",
                target_type=resource,
                target_id=entity.id,
                branch_id=_resource_branch_id(spec, entity),
                metadata={"fields": sorted(normalized)},
                before=before_price,
                after=_price_audit_value(resource=resource, values=normalized),
            )
            return _resource_view(spec, entity, actor=actor)

    async def archive_resource(
        self,
        *,
        actor: BookingActor,
        resource: str,
        resource_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Archive or deactivate a resource instead of deleting potentially referenced history."""

        spec = _resource_spec(resource)
        permission = _operation_permission(spec, operation="archive")
        actor.require(permission)
        async with self._database.session() as session, session.begin():
            entity = await _resource_for_update(
                session,
                spec=spec,
                organization_id=actor.organization_id,
                resource_id=resource_id,
                lock=True,
            )
            _require_resource_scope(actor=actor, spec=spec, permission=permission, entity=entity)
            if spec.archived_field is not None:
                setattr(
                    entity, spec.archived_field, require_aware(self._clock.now(), field_name="now")
                )
            if spec.active_field is not None:
                setattr(entity, spec.active_field, False)
            elif resource == "customers":
                entity.is_blocked = True
            else:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            _audit(
                session,
                actor=actor,
                event_type=f"{resource}.archived",
                target_type=resource,
                target_id=entity.id,
                reason=reason,
                branch_id=_resource_branch_id(spec, entity),
            )
            return _resource_view(spec, entity, actor=actor)

    async def update_settings(
        self,
        *,
        actor: BookingActor,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Update configured policy values, never silently fall back to hard-coded behavior."""

        actor.require(BookingPermission.SETTINGS_MANAGE)
        AccessPolicy.require_organization(actor, BookingPermission.SETTINGS_MANAGE)
        normalized = _normalize_settings(values)
        if not normalized:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        async with self._database.session() as session, session.begin():
            settings = await session.get(
                BookingSettings, actor.organization_id, with_for_update=True
            )
            if settings is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            for field, value in normalized.items():
                setattr(settings, field, value)
            _audit(
                session,
                actor=actor,
                event_type="settings.updated",
                target_type="settings",
                target_id=actor.organization_id,
                metadata={"fields": sorted(normalized)},
            )
            return _settings_view(settings)

    async def get_settings(self, *, actor: BookingActor) -> dict[str, Any]:
        """Return the single tenant-owned settings row for an authorized back-office actor."""

        actor.require(BookingPermission.SETTINGS_MANAGE)
        AccessPolicy.require_organization(actor, BookingPermission.SETTINGS_MANAGE)
        async with self._database.session() as session:
            settings = await session.get(BookingSettings, actor.organization_id)
            if settings is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            return _settings_view(settings)

    async def generate_staff_bind_code(
        self,
        *,
        actor: BookingActor,
        specialist_id: UUID,
        ttl_seconds: int = 900,
    ) -> dict[str, Any]:
        """Create a short-lived one-time code while storing only its SHA-256 digest."""

        actor.require(PermissionCode.ACCESS_BIND_CODES_CREATE)
        if ttl_seconds < 60 or ttl_seconds > 86_400:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        now = require_aware(self._clock.now(), field_name="now")
        raw_code = secrets.token_urlsafe(18)
        async with self._database.session() as session, session.begin():
            specialist = await session.scalar(
                sa.select(Specialist).where(
                    Specialist.id == specialist_id,
                    Specialist.organization_id == actor.organization_id,
                    Specialist.is_active.is_(True),
                    Specialist.archived_at.is_(None),
                )
            )
            if specialist is None:
                raise BookingDomainError(BookingErrorCode.SPECIALIST_INACTIVE)
            membership = await session.scalar(
                sa.select(BookingMembership).where(
                    BookingMembership.organization_id == actor.organization_id,
                    BookingMembership.specialist_id == specialist.id,
                    BookingMembership.is_active.is_(True),
                )
            )
            if membership is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            specialist_branch_ids = tuple(
                (
                    await session.scalars(
                        sa.select(SpecialistService.branch_id).where(
                            SpecialistService.organization_id == actor.organization_id,
                            SpecialistService.specialist_id == specialist.id,
                            SpecialistService.is_active.is_(True),
                        )
                    )
                ).all()
            )
            if specialist_branch_ids:
                for branch_id in specialist_branch_ids:
                    AccessPolicy.require_branch(
                        actor,
                        PermissionCode.ACCESS_BIND_CODES_CREATE,
                        branch_id,
                    )
            else:
                AccessPolicy.require_organization(actor, PermissionCode.ACCESS_BIND_CODES_CREATE)
            bind_code = StaffBindCode(
                organization_id=actor.organization_id,
                specialist_id=specialist.id,
                membership_id=membership.id,
                code_digest=hashlib.sha256(raw_code.encode("utf-8")).hexdigest(),
                expires_at=now + timedelta(seconds=ttl_seconds),
                created_by=actor.subject_id,
            )
            session.add(bind_code)
            await session.flush()
            _audit(
                session,
                actor=actor,
                event_type="staff_bind_code.generated",
                target_type="specialist",
                target_id=specialist.id,
                metadata={"expires_at": bind_code.expires_at.isoformat()},
            )
            return {
                "code": raw_code,
                "expires_at": bind_code.expires_at,
                "specialist_id": specialist.id,
            }

    async def consume_staff_bind_code(
        self,
        *,
        bot_app_id: str,
        telegram_user_id: str,
        telegram_chat_id: str,
        raw_code: str,
    ) -> UUID:
        """Bind a Telegram identity once, atomically, after server-side tenant resolution."""

        now = require_aware(self._clock.now(), field_name="now")
        digest = hashlib.sha256(raw_code.strip().encode("utf-8")).hexdigest()
        async with self._database.session() as session, session.begin():
            installation = await session.scalar(
                sa.select(BookingTelegramBotInstallation)
                .where(
                    BookingTelegramBotInstallation.bot_app_id == bot_app_id,
                    BookingTelegramBotInstallation.is_active.is_(True),
                )
                .with_for_update()
            )
            if installation is None:
                raise BookingDomainError(BookingErrorCode.INVALID_BIND_CODE)
            lock_key = (
                f"booking:staff_bind:{installation.organization_id}:{bot_app_id}:{telegram_user_id}"
            )
            await session.execute(
                sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key)))
            )
            bind_code = await session.scalar(
                sa.select(StaffBindCode)
                .where(
                    StaffBindCode.organization_id == installation.organization_id,
                    StaffBindCode.code_digest == digest,
                    StaffBindCode.used_at.is_(None),
                    StaffBindCode.revoked_at.is_(None),
                    StaffBindCode.expires_at > now,
                )
                .with_for_update()
            )
            if bind_code is None:
                raise BookingDomainError(BookingErrorCode.INVALID_BIND_CODE)
            membership = None
            if bind_code.membership_id is not None:
                membership = await session.scalar(
                    sa.select(BookingMembership).where(
                        BookingMembership.id == bind_code.membership_id,
                        BookingMembership.organization_id == installation.organization_id,
                        BookingMembership.is_active.is_(True),
                    )
                )
            if membership is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            existing_user = await session.scalar(
                sa.select(StaffTelegramBinding)
                .where(
                    StaffTelegramBinding.organization_id == installation.organization_id,
                    StaffTelegramBinding.bot_app_id == bot_app_id,
                    StaffTelegramBinding.telegram_user_id == telegram_user_id,
                    StaffTelegramBinding.is_active.is_(True),
                )
                .with_for_update()
            )
            if existing_user is not None and existing_user.specialist_id != bind_code.specialist_id:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            await session.execute(
                sa.update(StaffTelegramBinding)
                .where(
                    StaffTelegramBinding.organization_id == installation.organization_id,
                    StaffTelegramBinding.bot_app_id == bot_app_id,
                    StaffTelegramBinding.specialist_id == bind_code.specialist_id,
                    StaffTelegramBinding.is_active.is_(True),
                )
                .values(is_active=False)
            )
            if existing_user is None:
                session.add(
                    StaffTelegramBinding(
                        organization_id=installation.organization_id,
                        specialist_id=bind_code.specialist_id,
                        membership_id=membership.id,
                        bot_app_id=bot_app_id,
                        telegram_user_id=telegram_user_id,
                        telegram_chat_id=telegram_chat_id,
                        is_active=True,
                    )
                )
            else:
                existing_user.telegram_chat_id = telegram_chat_id
                existing_user.is_active = True
                existing_user.membership_id = membership.id
            bind_code.used_at = now
            append_audit_event(
                session,
                organization_id=installation.organization_id,
                action_code="staff_telegram.bound",
                actor_type=ActorType.TELEGRAM,
                target_type="specialist",
                target_id=bind_code.specialist_id,
                metadata={"bot_app_id": bot_app_id, "membership_id": str(membership.id)},
            )
            return bind_code.specialist_id


def _resource_spec(resource: str) -> ResourceSpec:
    """Resolve only a named supported aggregate and reject arbitrary model access."""

    try:
        return _RESOURCE_SPECS[resource]
    except KeyError as error:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error


async def _resource_for_update(
    session: AsyncSession,
    *,
    spec: ResourceSpec,
    organization_id: UUID,
    resource_id: UUID,
    lock: bool,
) -> Any:
    """Fetch one entity in tenant scope, optionally retaining a transactional row lock."""

    statement = sa.select(spec.model).where(
        spec.model.id == resource_id,
        spec.model.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    entity = await session.scalar(statement)
    if entity is None:
        raise BookingDomainError(BookingErrorCode.RESOURCE_NOT_FOUND)
    return entity


def _operation_permission(
    spec: ResourceSpec,
    *,
    operation: str,
) -> PermissionCode | BookingPermission:
    """Choose the narrowest configured permission for a generic resource operation."""

    if operation == "create":
        return spec.create_permission or spec.manage_permission or spec.permission
    if operation == "archive":
        return spec.archive_permission or spec.manage_permission or spec.permission
    return spec.manage_permission or spec.permission


def _scoped_resource_statement(
    *,
    actor: BookingActor,
    spec: ResourceSpec,
    permission: PermissionCode | BookingPermission,
    statement: Any,
) -> Any:
    """Attach an SQL scope predicate after the mandatory organization predicate is present."""

    if spec.branch_field is None:
        AccessPolicy.require_organization(actor, permission)
        return statement
    branch_column = getattr(spec.model, spec.branch_field)
    return statement.where(AccessPolicy.branch_predicate(actor, permission, branch_column))


def _require_resource_scope(
    *,
    actor: BookingActor,
    spec: ResourceSpec,
    permission: PermissionCode | BookingPermission,
    entity: Any,
) -> None:
    """Check a fetched row's concrete branch or require organization scope for global resources."""

    if spec.branch_field is None:
        AccessPolicy.require_organization(actor, permission)
        return
    AccessPolicy.require_branch(actor, permission, getattr(entity, spec.branch_field))


def _require_resource_create_scope(
    *,
    actor: BookingActor,
    spec: ResourceSpec,
    permission: PermissionCode | BookingPermission,
    values: Mapping[str, Any],
) -> None:
    """Prevent branch-scoped users from creating data outside their assigned branches."""

    if spec.branch_field is None or spec.branch_field not in values:
        AccessPolicy.require_organization(actor, permission)
        return
    branch_id = values[spec.branch_field]
    if not isinstance(branch_id, UUID):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    AccessPolicy.require_branch(actor, permission, branch_id)


def _require_resource_field_permissions(
    *,
    actor: BookingActor,
    resource: str,
    values: Mapping[str, Any],
) -> None:
    """Protect price-bearing catalog fields with their dedicated elevated permission."""

    if resource in {"services", "specialist-services"} and any(
        field in values for field in {"default_price", "custom_price"}
    ):
        AccessPolicy.require_organization(actor, PermissionCode.SERVICES_PRICES_MANAGE)


def _price_audit_value(*, resource: str, values: Mapping[str, Any]) -> dict[str, str] | None:
    """Record only safe old/new price values for elevated catalog price changes."""

    price_field = "default_price" if resource == "services" else "custom_price"
    value = values.get(price_field)
    return {price_field: str(value)} if value is not None else None


def _normalize_resource_values(
    spec: ResourceSpec,
    values: Mapping[str, Any],
    *,
    creating: bool,
) -> dict[str, Any]:
    """Reject mass assignment and normalize only fields declared by the resource contract."""

    unknown = set(values).difference(spec.fields)
    if unknown:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if creating and (
        not spec.required_fields.issubset(values)
        or any(values[field] is None for field in spec.required_fields)
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    normalized: dict[str, Any] = {}
    for field, value in values.items():
        normalized[field] = _coerce_value(field, value)
    _validate_local_field_invariants(normalized)
    return normalized


def _normalize_settings(values: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a strict settings whitelist and validate policy shapes before persistence."""

    fields = {
        "currency",
        "slot_step_minutes",
        "min_booking_lead_minutes",
        "max_booking_horizon_days",
        "hold_ttl_seconds",
        "client_cancellation_cutoff_minutes",
        "auto_confirm_booking",
        "require_client_phone",
        "prevent_customer_overlapping_appointments",
        "max_upcoming_appointments_per_customer",
        "reminder_offsets_minutes",
        "daily_staff_agenda_time",
        "allow_negative_stock",
        "require_open_cash_shift_for_cash_payment",
        "default_locale",
    }
    unknown = set(values).difference(fields)
    if unknown:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    normalized = {field: _coerce_value(field, value) for field, value in values.items()}
    if "currency" in normalized:
        currency = normalized["currency"]
        if not isinstance(currency, str) or len(currency) != 3:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        normalized["currency"] = currency.upper()
    if "default_locale" in normalized and normalized["default_locale"] not in {"ru", "uz", "en"}:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    _validate_local_field_invariants(normalized)
    return normalized


def _coerce_value(field: str, value: Any) -> Any:
    """Normalize JSON payload values into safe DB-native primitives without implicit truthiness."""

    nullable = {
        "category_id",
        "core_user_id",
        "description",
        "phone",
        "custom_duration_minutes",
        "custom_price",
        "custom_buffer_before_minutes",
        "custom_buffer_after_minutes",
        "reason",
        "last_name",
        "normalized_phone",
        "timezone",
        "notes",
        "sku",
        "low_stock_threshold",
        "warehouse_id",
        "customer_id",
        "specialist_id",
    }
    if value is None:
        if field in nullable:
            return None
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if field.endswith("_id") or field == "subject_id":
        try:
            return UUID(str(value))
        except (TypeError, ValueError) as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field in {
        "default_price",
        "custom_price",
        "low_stock_threshold",
        "quantity_required",
    }:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field in {
        "default_duration_minutes",
        "buffer_before_minutes",
        "buffer_after_minutes",
        "custom_duration_minutes",
        "custom_buffer_before_minutes",
        "custom_buffer_after_minutes",
        "sort_order",
        "weekday",
        "slot_step_minutes",
        "min_booking_lead_minutes",
        "max_booking_horizon_days",
        "hold_ttl_seconds",
        "client_cancellation_cutoff_minutes",
        "max_upcoming_appointments_per_customer",
    }:
        if not isinstance(value, int) or isinstance(value, bool):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return value
    if field in {
        "is_active",
        "booking_enabled",
        "accepts_bookings",
        "is_blocked",
        "is_default",
        "track_stock",
        "auto_confirm_booking",
        "require_client_phone",
        "prevent_customer_overlapping_appointments",
        "allow_negative_stock",
        "require_open_cash_shift_for_cash_payment",
    }:
        if not isinstance(value, bool):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return value
    if field in {"starts_at", "ends_at"}:
        if not isinstance(value, str):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        try:
            return require_aware(
                datetime.fromisoformat(value.replace("Z", "+00:00")), field_name=field
            )
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field in {"local_start_time", "local_end_time", "daily_staff_agenda_time"}:
        if not isinstance(value, str):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        try:
            return time.fromisoformat(value)
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field == "type":
        try:
            return AvailabilityExceptionType(str(value))
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field == "role":
        try:
            return AccessRole(str(value))
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if field == "permissions":
        if not isinstance(value, list):
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        permissions: list[str] = []
        for item in cast(list[object], value):
            if not isinstance(item, str):
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            permissions.append(item)
        return sorted(set(permissions))
    if field == "reminder_offsets_minutes":
        if not isinstance(value, list) or not value:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        offsets: list[int] = []
        for item in cast(list[object], value):
            if not isinstance(item, int) or isinstance(item, bool):
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            offsets.append(item)
        return sorted(set(offsets), reverse=True)
    if not isinstance(value, str):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return value.strip()


def _validate_local_field_invariants(values: Mapping[str, Any]) -> None:
    """Validate cross-field local values before SQL constraints become the last defense."""

    positive_fields = {
        "default_duration_minutes",
        "slot_step_minutes",
        "hold_ttl_seconds",
        "max_upcoming_appointments_per_customer",
        "quantity_required",
    }
    non_negative_fields = {
        "default_price",
        "custom_price",
        "low_stock_threshold",
        "buffer_before_minutes",
        "buffer_after_minutes",
        "custom_buffer_before_minutes",
        "custom_buffer_after_minutes",
        "min_booking_lead_minutes",
        "max_booking_horizon_days",
        "client_cancellation_cutoff_minutes",
    }
    for field in positive_fields:
        if field in values and values[field] <= 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    for field in non_negative_fields:
        if field in values and values[field] is not None and values[field] < 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if "weekday" in values and not 0 <= values["weekday"] <= 6:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if {
        "local_start_time",
        "local_end_time",
    }.issubset(values) and values["local_end_time"] <= values["local_start_time"]:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if {"starts_at", "ends_at"}.issubset(values) and values["ends_at"] <= values["starts_at"]:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    timezone = values.get("timezone")
    if timezone:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error


async def _validate_references(
    session: AsyncSession,
    *,
    organization_id: UUID,
    values: Mapping[str, Any],
) -> None:
    """Ensure every supplied foreign key belongs to this tenant before a mutation is allowed."""

    for field, model in _FOREIGN_MODELS.items():
        value = values.get(field)
        if value is None:
            continue
        found = await session.scalar(
            sa.select(model.id).where(
                model.id == value,
                model.organization_id == organization_id,
            )
        )
        if found is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)


async def _validate_schedule_interval(
    session: AsyncSession,
    *,
    organization_id: UUID,
    values: Mapping[str, Any],
    excluding_id: UUID | None = None,
) -> None:
    """Reject overlapping active weekly intervals before PostgreSQL backs the rule up."""

    if not values.get("is_active", True):
        return
    specialist_id = values.get("specialist_id")
    branch_id = values.get("branch_id")
    weekday = values.get("weekday")
    starts_at = values.get("local_start_time")
    ends_at = values.get("local_end_time")
    if not all(
        value is not None for value in (specialist_id, branch_id, weekday, starts_at, ends_at)
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    lock_key = f"booking:schedule:{organization_id}:{specialist_id}:{branch_id}:{weekday}"
    await session.execute(sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key))))
    statement = sa.select(WorkingSchedule.id).where(
        WorkingSchedule.organization_id == organization_id,
        WorkingSchedule.specialist_id == specialist_id,
        WorkingSchedule.branch_id == branch_id,
        WorkingSchedule.weekday == weekday,
        WorkingSchedule.is_active.is_(True),
        WorkingSchedule.local_start_time < ends_at,
        WorkingSchedule.local_end_time > starts_at,
    )
    if excluding_id is not None:
        statement = statement.where(WorkingSchedule.id != excluding_id)
    if await session.scalar(statement.limit(1)) is not None:
        raise BookingDomainError(
            BookingErrorCode.INVALID_REQUEST,
            "Working schedule intervals must not overlap.",
        )


def _resource_view(
    spec: ResourceSpec,
    entity: Any,
    *,
    actor: BookingActor,
) -> dict[str, Any]:
    """Produce a deliberately whitelisted generic admin representation from an ORM row."""

    result = {"id": entity.id}
    fields = spec.fields
    if spec.model is Customer and not actor.has(PermissionCode.CLIENTS_VIEW_SENSITIVE):
        fields = tuple(field for field in fields if field not in {"normalized_phone", "notes"})
    result.update({field: getattr(entity, field) for field in fields})
    if spec.archived_field is not None:
        result[spec.archived_field] = getattr(entity, spec.archived_field)
    for field in ("created_at", "updated_at"):
        if hasattr(entity, field):
            result[field] = getattr(entity, field)
    return result


def _settings_view(settings: BookingSettings) -> dict[str, Any]:
    """Map every configured policy field while omitting no behavior-affecting setting."""

    return {
        "currency": settings.currency,
        "slot_step_minutes": settings.slot_step_minutes,
        "min_booking_lead_minutes": settings.min_booking_lead_minutes,
        "max_booking_horizon_days": settings.max_booking_horizon_days,
        "hold_ttl_seconds": settings.hold_ttl_seconds,
        "client_cancellation_cutoff_minutes": settings.client_cancellation_cutoff_minutes,
        "auto_confirm_booking": settings.auto_confirm_booking,
        "require_client_phone": settings.require_client_phone,
        "prevent_customer_overlapping_appointments": (
            settings.prevent_customer_overlapping_appointments
        ),
        "max_upcoming_appointments_per_customer": settings.max_upcoming_appointments_per_customer,
        "reminder_offsets_minutes": settings.reminder_offsets_minutes,
        "daily_staff_agenda_time": settings.daily_staff_agenda_time,
        "allow_negative_stock": settings.allow_negative_stock,
        "require_open_cash_shift_for_cash_payment": (
            settings.require_open_cash_shift_for_cash_payment
        ),
        "default_locale": settings.default_locale,
        "updated_at": settings.updated_at,
    }


def _resource_branch_id(spec: ResourceSpec, entity: Any) -> UUID | None:
    """Extract an audit branch discriminator only from a declared resource scope field."""

    if spec.branch_field is None:
        return None
    value = getattr(entity, spec.branch_field)
    return value if isinstance(value, UUID) else None


def _audit(
    session: AsyncSession,
    *,
    actor: BookingActor,
    event_type: str,
    target_type: str,
    target_id: UUID,
    reason: str | None = None,
    branch_id: UUID | None = None,
    metadata: Mapping[str, Any] | None = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
) -> None:
    """Add an append-only audit event to the caller's existing transaction."""

    append_audit_event(
        session,
        organization_id=actor.organization_id,
        action_code=event_type,
        actor=actor,
        branch_id=branch_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        before=before,
        after=after,
        metadata=metadata,
    )
