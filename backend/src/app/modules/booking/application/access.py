"""Central live RBAC resolution, SQL scope policy, and idempotent registry synchronization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.booking.application.context import BookingActor, ScopedPermissionGrant
from app.modules.booking.application.permissions import (
    BUILTIN_ROLE_DEFINITIONS,
    LEGACY_ROLE_TO_BUILTIN_ROLE,
    PERMISSION_DEFINITIONS,
    BookingPermission,
    PermissionCode,
)
from app.modules.booking.domain.enums import (
    AccessRole,
    AccessScope,
    ActorType,
    AuditSource,
    BuiltInRole,
)
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.infrastructure.persistence.models import (
    Appointment,
    BookingAccessGrant,
    BookingMembership,
    BookingPermissionDefinition,
    BookingPlatformAdministrator,
    BookingRole,
    BookingRoleAssignment,
    BookingRoleAssignmentBranch,
    BookingRolePermission,
    Customer,
)

_SYSTEM_NAMESPACE = UUID("15e03440-0345-4576-aa89-a44c4bf142ba")
_CLIENT_PERMISSIONS = frozenset(
    {
        PermissionCode.BOOKINGS_CREATE.value,
        PermissionCode.BOOKINGS_VIEW.value,
        PermissionCode.BOOKINGS_RESCHEDULE.value,
        PermissionCode.BOOKINGS_CANCEL.value,
    }
)
_SYSTEM_OPERATION_PERMISSIONS: dict[str, frozenset[PermissionCode]] = {
    # Workers are named, tenant-scoped actors—not a hidden equivalent of an OWNER role.
    "hold_expiry": frozenset({PermissionCode.BOOKINGS_UPDATE}),
    "daily_agenda": frozenset({PermissionCode.BOOKINGS_VIEW, PermissionCode.STAFF_VIEW}),
}


@dataclass(frozen=True, slots=True)
class PlatformAdministratorAccess:
    """Verified platform identity intentionally detached from any tenant membership."""

    administrator_id: UUID
    subject_id: UUID
    access_version: int


class AccessPolicy:
    """The only scope evaluator used by services before reading or changing tenant data."""

    @staticmethod
    def require_branch(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        branch_id: UUID,
    ) -> None:
        """Require a capability and an organization/branch grant for one concrete branch."""

        if not AccessPolicy.allows_branch(actor, permission, branch_id):
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)

    @staticmethod
    def allows_branch(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        branch_id: UUID,
    ) -> bool:
        """Evaluate branch visibility without treating SELF as a branch-wide grant."""

        actor.require(permission)
        for grant in actor.grants_for(permission):
            if grant.scope is AccessScope.ORGANIZATION:
                return True
            if grant.scope is AccessScope.BRANCH and branch_id in grant.branch_ids:
                return True
        return False

    @staticmethod
    def require_organization(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
    ) -> None:
        """Require an organization-wide grant for data that cannot be safely branch-filtered."""

        actor.require(permission)
        if not any(
            grant.scope is AccessScope.ORGANIZATION for grant in actor.grants_for(permission)
        ):
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)

    @staticmethod
    def branch_predicate(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        branch_column: Any,
    ) -> Any:
        """Build an OR predicate for an already tenant-filtered branch-bearing query."""

        actor.require(permission)
        branch_ids: set[UUID] = set()
        for grant in actor.grants_for(permission):
            if grant.scope is AccessScope.ORGANIZATION:
                return sa.true()
            if grant.scope is AccessScope.BRANCH:
                branch_ids.update(grant.branch_ids)
        return branch_column.in_(branch_ids) if branch_ids else sa.false()

    @staticmethod
    def appointment_predicate(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        appointment: type[Appointment] = Appointment,
    ) -> Any:
        """Build a SQL predicate after the caller has constrained organization_id first."""

        actor.require(permission)
        clauses: list[Any] = []
        for grant in actor.grants_for(permission):
            if grant.scope is AccessScope.ORGANIZATION:
                return sa.true()
            if grant.scope is AccessScope.BRANCH and grant.branch_ids:
                clauses.append(appointment.branch_id.in_(grant.branch_ids))
            elif grant.scope is AccessScope.SELF and actor.specialist_id is not None:
                clauses.append(appointment.specialist_id == actor.specialist_id)
            elif grant.scope is AccessScope.CUSTOMER_OWN and actor.customer_id is not None:
                clauses.append(appointment.customer_id == actor.customer_id)
        return sa.or_(*clauses) if clauses else sa.false()

    @staticmethod
    def allows_appointment(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        *,
        branch_id: UUID,
        specialist_id: UUID,
        customer_id: UUID,
    ) -> bool:
        """Evaluate a loaded appointment with the same scope semantics as SQL filtering."""

        actor.require(permission)
        for grant in actor.grants_for(permission):
            if grant.scope is AccessScope.ORGANIZATION:
                return True
            if grant.scope is AccessScope.BRANCH and branch_id in grant.branch_ids:
                return True
            if grant.scope is AccessScope.SELF and actor.specialist_id == specialist_id:
                return True
            if grant.scope is AccessScope.CUSTOMER_OWN and actor.customer_id == customer_id:
                return True
        return False

    @staticmethod
    def require_appointment(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
        *,
        branch_id: UUID,
        specialist_id: UUID,
        customer_id: UUID,
    ) -> None:
        """Require scoped access to a loaded appointment before returning or changing it."""

        if not AccessPolicy.allows_appointment(
            actor,
            permission,
            branch_id=branch_id,
            specialist_id=specialist_id,
            customer_id=customer_id,
        ):
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)

    @staticmethod
    def branch_ids(
        actor: BookingActor,
        permission: PermissionCode | BookingPermission | str,
    ) -> frozenset[UUID] | None:
        """Return visible branch IDs, or None when organization scope is present."""

        actor.require(permission)
        ids: set[UUID] = set()
        for grant in actor.grants_for(permission):
            if grant.scope is AccessScope.ORGANIZATION:
                return None
            if grant.scope is AccessScope.BRANCH:
                ids.update(grant.branch_ids)
        return frozenset(ids)


class BookingAccessService:
    """Rehydrate staff authority from live memberships on every trusted boundary."""

    def __init__(self, *, database: Database, clock: Clock | None = None) -> None:
        self._database = database
        self._clock = clock or SystemClock()

    async def resolve_staff_actor(
        self,
        *,
        organization_id: UUID,
        subject_id: UUID | None,
        membership_id: UUID | None,
        access_version: int | None,
        source: AuditSource = AuditSource.API,
    ) -> BookingActor:
        """Return current permissions/scopes and reject revoked or stale staff sessions."""

        async with self._database.session() as session:
            membership = await self._membership_for_session(
                session,
                organization_id=organization_id,
                subject_id=subject_id,
                membership_id=membership_id,
            )
            if membership is None or not membership.is_active:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            if access_version is not None and membership.access_version != access_version:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            scoped_permissions, role_codes = await self._effective_grants(session, membership)
        return BookingActor(
            organization_id=membership.organization_id,
            subject_id=membership.subject_id,
            role=_display_role(role_codes, specialist_id=membership.specialist_id),
            permissions=frozenset(grant.code.value for grant in scoped_permissions),
            actor_type=ActorType.STAFF,
            specialist_id=membership.specialist_id,
            membership_id=membership.id,
            access_version=membership.access_version,
            scoped_permissions=scoped_permissions,
            audit_source=source,
        )

    async def resolve_client_actor(
        self,
        *,
        organization_id: UUID,
        subject_id: UUID,
        customer_id: UUID | None,
        source: AuditSource = AuditSource.API,
    ) -> BookingActor:
        """Revalidate the separate customer identity; no tenant role assignment is involved."""

        if customer_id is None or subject_id != customer_id:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        async with self._database.session() as session:
            customer = await session.scalar(
                sa.select(Customer).where(
                    Customer.id == customer_id,
                    Customer.organization_id == organization_id,
                )
            )
            if customer is None or customer.is_blocked:
                raise BookingDomainError(BookingErrorCode.CUSTOMER_BLOCKED)
            legacy_grant = await session.scalar(
                sa.select(BookingAccessGrant.is_active).where(
                    BookingAccessGrant.organization_id == organization_id,
                    BookingAccessGrant.subject_id == subject_id,
                    BookingAccessGrant.customer_id == customer_id,
                )
            )
            if legacy_grant is False:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        return BookingActor(
            organization_id=organization_id,
            subject_id=subject_id,
            role=AccessRole.CUSTOMER,
            permissions=_CLIENT_PERMISSIONS,
            actor_type=ActorType.CUSTOMER,
            customer_id=customer_id,
            audit_source=source,
        )

    async def actor_for_staff_binding(
        self,
        *,
        organization_id: UUID,
        subject_id: UUID | None,
        membership_id: UUID | None,
        specialist_id: UUID,
        source: AuditSource = AuditSource.TELEGRAM,
    ) -> BookingActor:
        """Resolve a Telegram binding through membership, creating a safe legacy bridge once."""

        if membership_id is None:
            if subject_id is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            membership_id = await self._materialize_legacy_membership(
                organization_id=organization_id,
                subject_id=subject_id,
                specialist_id=specialist_id,
            )
        return await self.resolve_staff_actor(
            organization_id=organization_id,
            subject_id=subject_id,
            membership_id=membership_id,
            access_version=None,
            source=source,
        )

    def system_actor(
        self,
        *,
        organization_id: UUID,
        task_id: str,
        operation: str,
        branch_ids: frozenset[UUID] = frozenset(),
    ) -> BookingActor:
        """Create bounded worker authority for one named operation and tenant scope."""

        permissions = _SYSTEM_OPERATION_PERMISSIONS.get(operation)
        if permissions is None:
            raise ValueError(f"Unknown booking worker operation: {operation}")
        subject_id = uuid5(_SYSTEM_NAMESPACE, f"booking:{organization_id}:{task_id}")
        grants = tuple(
            ScopedPermissionGrant(
                permission,
                AccessScope.BRANCH if branch_ids else AccessScope.ORGANIZATION,
                branch_ids=branch_ids,
            )
            for permission in permissions
        )
        return BookingActor(
            organization_id=organization_id,
            subject_id=subject_id,
            role=AccessRole.ADMIN,
            permissions=frozenset(permission.value for permission in permissions),
            actor_type=ActorType.SYSTEM,
            scoped_permissions=grants,
            audit_source=AuditSource.WORKER,
            task_id=task_id,
        )

    async def _membership_for_session(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        subject_id: UUID | None,
        membership_id: UUID | None,
    ) -> BookingMembership | None:
        """Load exactly the requested tenant membership; no cross-tenant fallback is possible."""

        statement = sa.select(BookingMembership).where(
            BookingMembership.organization_id == organization_id,
        )
        if subject_id is not None:
            statement = statement.where(BookingMembership.subject_id == subject_id)
        if membership_id is not None:
            statement = statement.where(BookingMembership.id == membership_id)
        return await session.scalar(statement)

    async def _effective_grants(
        self,
        session: AsyncSession,
        membership: BookingMembership,
    ) -> tuple[tuple[ScopedPermissionGrant, ...], tuple[str, ...]]:
        """Load assignments, roles, permissions and branch mapping in one joined query."""

        now = self._clock.now()
        result = await session.execute(
            sa.select(
                BookingRoleAssignment,
                BookingRole.code,
                BookingRolePermission.permission_code,
                BookingRoleAssignmentBranch.branch_id,
            )
            .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
            .outerjoin(
                BookingRolePermission,
                BookingRolePermission.role_id == BookingRole.id,
            )
            .outerjoin(
                BookingRoleAssignmentBranch,
                BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
            )
            .where(
                BookingRoleAssignment.organization_id == membership.organization_id,
                BookingRoleAssignment.membership_id == membership.id,
                BookingRoleAssignment.is_active.is_(True),
                BookingRole.is_active.is_(True),
                sa.or_(
                    BookingRole.organization_id.is_(None),
                    BookingRole.organization_id == membership.organization_id,
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
        )
        assignments: dict[UUID, _AssignmentMaterial] = {}
        for assignment, role_code, raw_permission, branch_id in result.all():
            material = assignments.setdefault(
                assignment.id,
                _AssignmentMaterial(
                    assignment_id=assignment.id,
                    scope=assignment.scope,
                    role_code=role_code,
                ),
            )
            if raw_permission is not None:
                try:
                    material.permission_codes.add(PermissionCode(raw_permission))
                except ValueError:
                    continue
            if branch_id is not None:
                material.branch_ids.add(branch_id)
        grants: list[ScopedPermissionGrant] = []
        role_codes: list[str] = []
        for material in assignments.values():
            role_codes.append(material.role_code)
            for permission in material.permission_codes:
                grants.append(
                    ScopedPermissionGrant(
                        code=permission,
                        scope=material.scope,
                        branch_ids=frozenset(material.branch_ids),
                        role_assignment_id=material.assignment_id,
                        role_code=material.role_code,
                    )
                )
        return tuple(grants), tuple(role_codes)

    async def _materialize_legacy_membership(
        self,
        *,
        organization_id: UUID,
        subject_id: UUID,
        specialist_id: UUID,
    ) -> UUID:
        """One-time compatibility bridge for a pre-RBAC staff Telegram binding."""

        async with self._database.session() as session, session.begin():
            membership = await session.scalar(
                sa.select(BookingMembership)
                .where(
                    BookingMembership.organization_id == organization_id,
                    BookingMembership.subject_id == subject_id,
                )
                .with_for_update()
            )
            if membership is not None:
                return membership.id
            grant = await session.scalar(
                sa.select(BookingAccessGrant)
                .where(
                    BookingAccessGrant.organization_id == organization_id,
                    BookingAccessGrant.subject_id == subject_id,
                    BookingAccessGrant.specialist_id == specialist_id,
                    BookingAccessGrant.is_active.is_(True),
                )
                .with_for_update()
            )
            if grant is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            membership = BookingMembership(
                organization_id=organization_id,
                subject_id=subject_id,
                specialist_id=specialist_id,
                is_active=True,
            )
            session.add(membership)
            await session.flush()
            built_in = LEGACY_ROLE_TO_BUILTIN_ROLE.get(grant.role, BuiltInRole.SPECIALIST)
            role = await session.scalar(
                sa.select(BookingRole).where(
                    BookingRole.organization_id.is_(None),
                    BookingRole.code == built_in.value,
                )
            )
            if role is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            assignment = BookingRoleAssignment(
                organization_id=organization_id,
                membership_id=membership.id,
                role_id=role.id,
                scope=AccessScope.ORGANIZATION,
                assigned_by=grant.subject_id,
            )
            session.add(assignment)
            return membership.id


class BookingPlatformAccessService:
    """Resolve platform administrators only for a dedicated internal-auth boundary.

    This service deliberately returns no ``BookingActor``: tenant services cannot accidentally
    treat a platform administrator as an organization owner or reuse tenant bearer sessions.
    """

    def __init__(self, *, database: Database) -> None:
        self._database = database

    async def resolve_administrator(
        self,
        *,
        subject_id: UUID,
        access_version: int | None = None,
    ) -> PlatformAdministratorAccess:
        """Validate a platform-only principal and optionally reject a revoked stale session."""

        async with self._database.session() as session:
            administrator = await session.scalar(
                sa.select(BookingPlatformAdministrator).where(
                    BookingPlatformAdministrator.subject_id == subject_id,
                    BookingPlatformAdministrator.is_active.is_(True),
                )
            )
        if administrator is None:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        if access_version is not None and administrator.access_version != access_version:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        return PlatformAdministratorAccess(
            administrator_id=administrator.id,
            subject_id=administrator.subject_id,
            access_version=administrator.access_version,
        )


@dataclass(slots=True)
class _AssignmentMaterial:
    """Mutable grouping used only while flattening one SQL join into immutable actor grants."""

    assignment_id: UUID
    scope: AccessScope
    role_code: str
    permission_codes: set[PermissionCode] = field(default_factory=lambda: set[PermissionCode]())
    branch_ids: set[UUID] = field(default_factory=lambda: set[UUID]())


class RbacSynchronizer:
    """Atomically seed/update registry metadata and immutable built-in role permission mappings."""

    def __init__(self, *, database: Database) -> None:
        self._database = database

    async def synchronize(self) -> None:
        """Synchronize the source-controlled registry without touching tenant custom roles."""

        async with self._database.session() as session, session.begin():
            await self.synchronize_session(session)

    async def synchronize_session(self, session: AsyncSession) -> None:
        """Make one open transaction converge to the known permission and role definitions."""

        for definition in PERMISSION_DEFINITIONS:
            entity = await session.get(BookingPermissionDefinition, definition.code.value)
            values = {
                "name": definition.name,
                "description": definition.description,
                "category": definition.category,
                "allowed_scopes": sorted(scope.value for scope in definition.allowed_scopes),
                "is_sensitive": definition.is_sensitive,
                "is_active": True,
            }
            if entity is None:
                session.add(BookingPermissionDefinition(code=definition.code.value, **values))
            else:
                for field, value in values.items():
                    setattr(entity, field, value)
        await session.flush()
        for definition in BUILTIN_ROLE_DEFINITIONS:
            role = await session.scalar(
                sa.select(BookingRole).where(
                    BookingRole.organization_id.is_(None),
                    BookingRole.code == definition.code.value,
                )
            )
            if role is None:
                role = BookingRole(
                    organization_id=None,
                    code=definition.code.value,
                    name=definition.name,
                    description=definition.description,
                    is_system=True,
                    is_active=True,
                )
                session.add(role)
                await session.flush()
            else:
                role.name = definition.name
                role.description = definition.description
                role.is_system = True
                role.is_active = True
            existing = set(
                (
                    await session.scalars(
                        sa.select(BookingRolePermission).where(
                            BookingRolePermission.role_id == role.id
                        )
                    )
                ).all()
            )
            expected = {permission.value for permission in definition.permissions}
            for relation in existing:
                if relation.permission_code not in expected:
                    await session.delete(relation)
            existing_codes = {relation.permission_code for relation in existing}
            for permission_code in expected - existing_codes:
                session.add(BookingRolePermission(role_id=role.id, permission_code=permission_code))


def _display_role(role_codes: Iterable[str], *, specialist_id: UUID | None) -> AccessRole:
    """Provide a legacy-safe display role; access always comes from scoped permissions instead."""

    priorities = tuple(BuiltInRole)
    known = set(role_codes)
    for code in priorities:
        if code.value in known:
            try:
                return AccessRole(code.value.lower())
            except ValueError:
                continue
    return AccessRole.SPECIALIST if specialist_id is not None else AccessRole.ADMIN
