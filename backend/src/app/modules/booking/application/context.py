"""Explicit tenant, actor, and scoped-permission context passed to booking use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.booking.application.permissions import (
    BookingPermission,
    PermissionCode,
    effective_permissions,
    normalize_permission,
    require_permission,
)
from app.modules.booking.domain.enums import AccessRole, AccessScope, ActorType, AuditSource


@dataclass(frozen=True, slots=True)
class ScopedPermissionGrant:
    """One effective permission inherited from a live role assignment and its scope."""

    code: PermissionCode
    scope: AccessScope
    branch_ids: frozenset[UUID] = frozenset()
    role_assignment_id: UUID | None = None
    role_code: str | None = None


@dataclass(frozen=True, slots=True)
class BookingActor:
    """A verified tenant-scoped subject; client data never supplies these values."""

    organization_id: UUID
    subject_id: UUID
    role: AccessRole
    permissions: frozenset[str]
    actor_type: ActorType
    customer_id: UUID | None = None
    specialist_id: UUID | None = None
    membership_id: UUID | None = None
    access_version: int | None = None
    scoped_permissions: tuple[ScopedPermissionGrant, ...] = ()
    audit_source: AuditSource = AuditSource.API
    request_id: str | None = None
    correlation_id: str | None = None
    task_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    @property
    def effective_permissions(self) -> frozenset[BookingPermission]:
        """Compatibility view for legacy booking services during the RBAC transition."""

        if self.membership_id is None and not self.scoped_permissions:
            return effective_permissions(role=self.role, explicit_permissions=self.permissions)
        values = {permission.value for permission in BookingPermission}
        return frozenset(BookingPermission(value) for value in self.permissions if value in values)

    @property
    def is_client(self) -> bool:
        """Return whether this is the separate customer-owned booking path."""

        return self.role is AccessRole.CUSTOMER and self.customer_id is not None

    @property
    def is_system(self) -> bool:
        """Return whether a named worker/internal system context issued this actor."""

        return self.actor_type is ActorType.SYSTEM

    @property
    def permission_codes(self) -> frozenset[str]:
        """Return display-safe effective codes while keeping token authority server-side."""

        if self.membership_id is not None or self.scoped_permissions:
            return self.permissions
        return frozenset(normalize_permission(value).value for value in self.effective_permissions)

    def require(self, permission: PermissionCode | BookingPermission | str) -> None:
        """Ensure the centrally registered capability is present before any mutation/query."""

        if not self.has(permission):
            require_permission(frozenset(), permission)

    def has(self, permission: PermissionCode | BookingPermission | str) -> bool:
        """Return whether this verified actor has a capability, never trusting client claims."""

        canonical = normalize_permission(permission)
        if self.membership_id is not None or self.scoped_permissions:
            return canonical.value in self.permissions
        return canonical.value in {
            normalize_permission(value).value for value in self.effective_permissions
        }

    def grants_for(
        self,
        permission: PermissionCode | BookingPermission | str,
    ) -> tuple[ScopedPermissionGrant, ...]:
        """Return only live materialized scoped grants for the requested capability."""

        canonical = normalize_permission(permission)
        explicit = tuple(grant for grant in self.scoped_permissions if grant.code is canonical)
        if explicit:
            return explicit
        if not self.has(canonical):
            return ()
        if self.is_client:
            return (ScopedPermissionGrant(canonical, AccessScope.CUSTOMER_OWN),)
        if self.membership_id is not None:
            return ()
        if self.role is AccessRole.SPECIALIST and self.specialist_id is not None:
            return (ScopedPermissionGrant(canonical, AccessScope.SELF),)
        return (ScopedPermissionGrant(canonical, AccessScope.ORGANIZATION),)
