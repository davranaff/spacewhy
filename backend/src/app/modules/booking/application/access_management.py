"""Tenant RBAC administration with scope validation, immediate revocation, and audit events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.booking.application.access import AccessPolicy
from app.modules.booking.application.audit import append_audit_event
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.permissions import (
    PERMISSION_BY_CODE,
    SAFE_BRANCH_MANAGER_ROLE_CODES,
    PermissionCode,
    normalize_permission,
)
from app.modules.booking.domain.enums import AccessScope, BuiltInRole
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.infrastructure.persistence.models import (
    BookingAuditLog,
    BookingBranch,
    BookingMembership,
    BookingPermissionDefinition,
    BookingRole,
    BookingRoleAssignment,
    BookingRoleAssignmentBranch,
    BookingRolePermission,
    Specialist,
    StaffBindCode,
)


@dataclass(frozen=True, slots=True)
class RoleAssignmentInput:
    """Validated caller intent for one role assignment; it never contains authority claims."""

    role_id: UUID
    scope: AccessScope
    branch_ids: tuple[UUID, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class BookingAccessManagementService:
    """Only service allowed to change membership, role, assignment, and access-version state."""

    def __init__(self, *, database: Database, clock: Clock | None = None) -> None:
        self._database = database
        self._clock = clock or SystemClock()

    async def my_access(self, *, actor: BookingActor) -> dict[str, Any]:
        """Return the current server-derived effective access snapshot for UI capability gating."""

        roles: dict[UUID, dict[str, Any]] = {}
        scopes_by_permission: dict[str, list[dict[str, Any]]] = defaultdict(list)
        branch_ids: set[UUID] = set()
        has_organization_scope = False
        for grant in actor.scoped_permissions:
            if grant.role_assignment_id is not None:
                role = roles.setdefault(
                    grant.role_assignment_id,
                    {
                        "assignment_id": grant.role_assignment_id,
                        "code": grant.role_code,
                        "scope": grant.scope.value,
                        "branch_ids": sorted(grant.branch_ids, key=str),
                    },
                )
                role["branch_ids"] = sorted(
                    set(role["branch_ids"]).union(grant.branch_ids),
                    key=str,
                )
            scope_value = {
                "scope": grant.scope.value,
                "branch_ids": sorted(grant.branch_ids, key=str),
            }
            if scope_value not in scopes_by_permission[grant.code.value]:
                scopes_by_permission[grant.code.value].append(scope_value)
            if grant.scope is AccessScope.ORGANIZATION:
                has_organization_scope = True
            if grant.scope is AccessScope.BRANCH:
                branch_ids.update(grant.branch_ids)
        if has_organization_scope:
            async with self._database.session() as session:
                branch_ids = set(
                    (
                        await session.scalars(
                            sa.select(BookingBranch.id).where(
                                BookingBranch.organization_id == actor.organization_id,
                                BookingBranch.is_active.is_(True),
                            )
                        )
                    ).all()
                )
        return {
            "organization_id": actor.organization_id,
            "membership_id": actor.membership_id,
            "subject_id": actor.subject_id,
            "role": actor.role.value,
            "specialist_id": actor.specialist_id,
            "roles": list(roles.values()),
            "permissions": sorted(actor.permissions),
            "permission_scopes": dict(scopes_by_permission),
            "accessible_branch_ids": sorted(branch_ids, key=str),
            "capabilities": {
                "can_manage_roles": actor.has(PermissionCode.ACCESS_ROLES_MANAGE),
                "can_view_finance": actor.has(PermissionCode.ANALYTICS_FINANCE_VIEW),
                "can_refund": actor.has(PermissionCode.CASH_REFUNDS_CREATE),
            },
            "access_version": actor.access_version,
        }

    async def list_permissions(self, *, actor: BookingActor) -> tuple[dict[str, Any], ...]:
        """Expose registry metadata only to a role-administration reader."""

        actor.require(PermissionCode.ACCESS_ROLES_VIEW)
        async with self._database.session() as session:
            rows = (
                await session.scalars(
                    sa.select(BookingPermissionDefinition)
                    .where(BookingPermissionDefinition.is_active.is_(True))
                    .order_by(
                        BookingPermissionDefinition.category,
                        BookingPermissionDefinition.code,
                    )
                )
            ).all()
        return tuple(
            {
                "code": row.code,
                "name": row.name,
                "description": row.description,
                "category": row.category,
                "allowed_scopes": row.allowed_scopes,
                "is_sensitive": row.is_sensitive,
            }
            for row in rows
        )

    async def list_roles(self, *, actor: BookingActor) -> tuple[dict[str, Any], ...]:
        """List global built-ins plus only custom roles in the caller's organization."""

        actor.require(PermissionCode.ACCESS_ROLES_VIEW)
        async with self._database.session() as session:
            rows = (
                await session.execute(
                    sa.select(BookingRole, BookingRolePermission.permission_code)
                    .outerjoin(
                        BookingRolePermission,
                        BookingRolePermission.role_id == BookingRole.id,
                    )
                    .where(
                        sa.or_(
                            BookingRole.organization_id.is_(None),
                            BookingRole.organization_id == actor.organization_id,
                        ),
                        BookingRole.is_active.is_(True),
                    )
                    .order_by(BookingRole.is_system.desc(), BookingRole.code)
                )
            ).all()
        grouped: dict[UUID, dict[str, Any]] = {}
        for role, permission_code in rows:
            item = grouped.setdefault(
                role.id,
                {
                    "id": role.id,
                    "code": role.code,
                    "name": role.name,
                    "description": role.description,
                    "is_system": role.is_system,
                    "permissions": [],
                },
            )
            if permission_code is not None:
                item["permissions"].append(permission_code)
        return tuple(grouped.values())

    async def create_custom_role(
        self,
        *,
        actor: BookingActor,
        code: str,
        name: str,
        description: str | None,
        permission_codes: Sequence[str],
    ) -> dict[str, Any]:
        """Create a tenant-local role from known permissions the assigning actor already has."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_MANAGE)
        normalized_code = _custom_role_code(code)
        permissions = _normalize_permission_codes(permission_codes)
        _require_actor_can_grant(actor, permissions)
        async with self._database.session() as session, session.begin():
            role = BookingRole(
                organization_id=actor.organization_id,
                code=normalized_code,
                name=_required_text(name, maximum=160),
                description=(description or "").strip()[:5_000],
                is_system=False,
                is_active=True,
                created_by=actor.subject_id,
                updated_by=actor.subject_id,
            )
            session.add(role)
            try:
                await session.flush()
            except IntegrityError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            session.add_all(
                BookingRolePermission(role_id=role.id, permission_code=permission.value)
                for permission in permissions
            )
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.role.created",
                actor=actor,
                target_type="role",
                target_id=role.id,
                after={"code": role.code, "permissions": sorted(p.value for p in permissions)},
            )
        return _role_view(role, permissions)

    async def update_custom_role(
        self,
        *,
        actor: BookingActor,
        role_id: UUID,
        name: str | None,
        description: str | None,
        permission_codes: Sequence[str] | None,
    ) -> dict[str, Any]:
        """Modify only a tenant custom role and converge its permission set atomically."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_MANAGE)
        async with self._database.session() as session, session.begin():
            role = await self._role_for_update(session, actor=actor, role_id=role_id)
            if role.is_system:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            before_codes = set(
                (
                    await session.scalars(
                        sa.select(BookingRolePermission.permission_code).where(
                            BookingRolePermission.role_id == role.id
                        )
                    )
                ).all()
            )
            if name is not None:
                role.name = _required_text(name, maximum=160)
            if description is not None:
                role.description = description.strip()[:5_000]
            permission_values = before_codes
            if permission_codes is not None:
                normalized = _normalize_permission_codes(permission_codes)
                _require_actor_can_grant(actor, normalized)
                permission_values = {permission.value for permission in normalized}
                await session.execute(
                    sa.delete(BookingRolePermission).where(BookingRolePermission.role_id == role.id)
                )
                session.add_all(
                    BookingRolePermission(role_id=role.id, permission_code=value)
                    for value in sorted(permission_values)
                )
            role.updated_by = actor.subject_id
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.role.updated",
                actor=actor,
                target_type="role",
                target_id=role.id,
                before={"permissions": sorted(before_codes)},
                after={"permissions": sorted(permission_values)},
            )
        return _role_view(role, tuple(PermissionCode(value) for value in permission_values))

    async def clone_role(
        self,
        *,
        actor: BookingActor,
        source_role_id: UUID,
        code: str,
        name: str,
        description: str | None,
    ) -> dict[str, Any]:
        """Clone a system or tenant role into a separately auditable tenant custom role."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_MANAGE)
        normalized_code = _custom_role_code(code)
        async with self._database.session() as session, session.begin():
            source_role = await self._role_for_update(
                session,
                actor=actor,
                role_id=source_role_id,
            )
            if not source_role.is_active:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            permission_codes = set(
                (
                    await session.scalars(
                        sa.select(BookingRolePermission.permission_code).where(
                            BookingRolePermission.role_id == source_role.id
                        )
                    )
                ).all()
            )
            permissions = tuple(PermissionCode(value) for value in permission_codes)
            _require_actor_can_grant(actor, permissions)
            role = BookingRole(
                organization_id=actor.organization_id,
                code=normalized_code,
                name=_required_text(name, maximum=160),
                description=(description or source_role.description).strip()[:5_000],
                is_system=False,
                is_active=True,
                created_by=actor.subject_id,
                updated_by=actor.subject_id,
            )
            session.add(role)
            try:
                await session.flush()
            except IntegrityError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            session.add_all(
                BookingRolePermission(role_id=role.id, permission_code=permission.value)
                for permission in permissions
            )
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.role.cloned",
                actor=actor,
                target_type="role",
                target_id=role.id,
                before={"source_role_id": str(source_role.id)},
                after={
                    "code": role.code,
                    "permissions": sorted(item.value for item in permissions),
                },
            )
        return _role_view(role, permissions)

    async def deactivate_custom_role(
        self,
        *,
        actor: BookingActor,
        role_id: UUID,
        reason: str | None,
    ) -> None:
        """Disable a custom role and invalidate every currently assigned membership."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_MANAGE)
        async with self._database.session() as session, session.begin():
            role = await self._role_for_update(session, actor=actor, role_id=role_id)
            if role.is_system:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            if not role.is_active:
                return
            memberships = (
                await session.scalars(
                    sa.select(BookingMembership)
                    .join(
                        BookingRoleAssignment,
                        BookingRoleAssignment.membership_id == BookingMembership.id,
                    )
                    .where(
                        BookingRoleAssignment.role_id == role.id,
                        BookingRoleAssignment.is_active.is_(True),
                    )
                    .with_for_update()
                )
            ).all()
            role.is_active = False
            role.updated_by = actor.subject_id
            for membership in memberships:
                _bump_access_version(membership)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.role.deactivated",
                actor=actor,
                target_type="role",
                target_id=role.id,
                reason=reason,
            )

    async def delete_custom_role(
        self,
        *,
        actor: BookingActor,
        role_id: UUID,
        reason: str | None,
    ) -> None:
        """Delete an unused custom role; role history remains safe through its audit record."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_MANAGE)
        async with self._database.session() as session, session.begin():
            role = await self._role_for_update(session, actor=actor, role_id=role_id)
            if role.is_system:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            assignment_exists = await session.scalar(
                sa.select(BookingRoleAssignment.id)
                .where(BookingRoleAssignment.role_id == role.id)
                .limit(1)
            )
            if assignment_exists is not None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.role.deleted",
                actor=actor,
                target_type="role",
                target_id=role.id,
                reason=reason,
                before={"code": role.code},
            )
            await session.delete(role)

    async def list_members(self, *, actor: BookingActor) -> tuple[dict[str, Any], ...]:
        """List memberships under organization scope or only branch-assigned membership roles."""

        actor.require(PermissionCode.ACCESS_MEMBERS_VIEW)
        visible_branches = AccessPolicy.branch_ids(actor, PermissionCode.ACCESS_MEMBERS_VIEW)
        now = self._clock.now()
        async with self._database.session() as session:
            statement = sa.select(BookingMembership).where(
                BookingMembership.organization_id == actor.organization_id
            )
            if visible_branches is not None:
                statement = (
                    statement.join(
                        BookingRoleAssignment,
                        BookingRoleAssignment.membership_id == BookingMembership.id,
                    )
                    .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
                    .join(
                        BookingRoleAssignmentBranch,
                        BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
                    )
                    .where(
                        BookingRoleAssignment.is_active.is_(True),
                        BookingRole.is_active.is_(True),
                        sa.or_(
                            BookingRole.organization_id.is_(None),
                            BookingRole.organization_id == actor.organization_id,
                        ),
                        BookingRoleAssignmentBranch.branch_id.in_(visible_branches),
                        sa.or_(
                            BookingRoleAssignment.starts_at.is_(None),
                            BookingRoleAssignment.starts_at <= now,
                        ),
                        sa.or_(
                            BookingRoleAssignment.ends_at.is_(None),
                            BookingRoleAssignment.ends_at > now,
                        ),
                    )
                    .distinct()
                )
            members = (
                await session.scalars(
                    statement.order_by(BookingMembership.created_at, BookingMembership.id)
                )
            ).all()
            return await self._member_views(
                session,
                memberships=members,
                visible_branch_ids=visible_branches,
            )

    async def member_access(
        self,
        *,
        actor: BookingActor,
        membership_id: UUID,
    ) -> dict[str, Any]:
        """Return one visible membership's live permissions without client-side inference."""

        actor.require(PermissionCode.ACCESS_MEMBERS_VIEW)
        visible_branches = AccessPolicy.branch_ids(actor, PermissionCode.ACCESS_MEMBERS_VIEW)
        now = self._clock.now()
        async with self._database.session() as session:
            membership = await session.scalar(
                sa.select(BookingMembership).where(
                    BookingMembership.id == membership_id,
                    BookingMembership.organization_id == actor.organization_id,
                )
            )
            if membership is None:
                raise BookingDomainError(BookingErrorCode.RESOURCE_NOT_FOUND)
            if visible_branches is not None:
                visible_assignment = await session.scalar(
                    sa.select(BookingRoleAssignment.id)
                    .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
                    .join(
                        BookingRoleAssignmentBranch,
                        BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
                    )
                    .where(
                        BookingRoleAssignment.membership_id == membership.id,
                        BookingRoleAssignment.organization_id == actor.organization_id,
                        BookingRoleAssignment.is_active.is_(True),
                        BookingRole.is_active.is_(True),
                        sa.or_(
                            BookingRole.organization_id.is_(None),
                            BookingRole.organization_id == actor.organization_id,
                        ),
                        BookingRoleAssignmentBranch.branch_id.in_(visible_branches),
                        sa.or_(
                            BookingRoleAssignment.starts_at.is_(None),
                            BookingRoleAssignment.starts_at <= now,
                        ),
                        sa.or_(
                            BookingRoleAssignment.ends_at.is_(None),
                            BookingRoleAssignment.ends_at > now,
                        ),
                    )
                    .limit(1)
                )
                if visible_assignment is None:
                    raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            statement = (
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
                    BookingRoleAssignment.membership_id == membership.id,
                    BookingRoleAssignment.organization_id == actor.organization_id,
                    BookingRoleAssignment.is_active.is_(True),
                    BookingRole.is_active.is_(True),
                    sa.or_(
                        BookingRole.organization_id.is_(None),
                        BookingRole.organization_id == actor.organization_id,
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
            if visible_branches is not None:
                statement = statement.where(
                    BookingRoleAssignment.scope == AccessScope.BRANCH,
                    BookingRoleAssignmentBranch.branch_id.in_(visible_branches),
                )
            rows = (await session.execute(statement)).all()
            assignments: dict[UUID, dict[str, Any]] = {}
            for assignment, role_code, permission_code, branch_id in rows:
                item = assignments.setdefault(
                    assignment.id,
                    {
                        "role_code": role_code,
                        "scope": assignment.scope.value,
                        "branch_ids": set(),
                        "permissions": set(),
                    },
                )
                if branch_id is not None:
                    cast(set[UUID], item["branch_ids"]).add(branch_id)
                if permission_code is not None:
                    cast(set[str], item["permissions"]).add(permission_code)
            permission_scopes: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in assignments.values():
                scope = {
                    "scope": item["scope"],
                    "branch_ids": sorted(cast(set[UUID], item["branch_ids"]), key=str),
                }
                for permission in cast(set[str], item["permissions"]):
                    if scope not in permission_scopes[permission]:
                        permission_scopes[permission].append(scope)
            return {
                "membership_id": membership.id,
                "is_active": membership.is_active,
                "access_version": membership.access_version,
                "permissions": sorted(permission_scopes),
                "permission_scopes": dict(permission_scopes),
            }

    async def create_member(
        self,
        *,
        actor: BookingActor,
        subject_id: UUID,
        specialist_id: UUID | None,
        display_name: str | None,
        assignments: Sequence[RoleAssignmentInput],
    ) -> dict[str, Any]:
        """Create a staff membership and its scoped roles as one transaction."""

        actor.require(PermissionCode.ACCESS_MEMBERS_INVITE)
        if not assignments:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        async with self._database.session() as session, session.begin():
            if specialist_id is not None:
                specialist = await session.scalar(
                    sa.select(Specialist).where(
                        Specialist.id == specialist_id,
                        Specialist.organization_id == actor.organization_id,
                    )
                )
                if specialist is None:
                    raise BookingDomainError(BookingErrorCode.SPECIALIST_INACTIVE)
            membership = BookingMembership(
                organization_id=actor.organization_id,
                subject_id=subject_id,
                specialist_id=specialist_id,
                display_name=display_name.strip()[:200] if display_name else None,
                is_active=True,
                access_version=1,
            )
            session.add(membership)
            try:
                await session.flush()
            except IntegrityError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            created_assignments = [
                await self._create_assignment(
                    session,
                    actor=actor,
                    membership=membership,
                    input_value=input_value,
                )
                for input_value in assignments
            ]
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.member.created",
                actor=actor,
                target_type="membership",
                target_id=membership.id,
                after={"assignment_ids": [str(item.id) for item in created_assignments]},
            )
            result = await self._member_view(session, membership=membership)
        return result

    async def assign_role(
        self,
        *,
        actor: BookingActor,
        membership_id: UUID,
        input_value: RoleAssignmentInput,
    ) -> dict[str, Any]:
        """Add a checked scoped role assignment and invalidate bearer sessions immediately."""

        actor.require(PermissionCode.ACCESS_ROLES_ASSIGN)
        async with self._database.session() as session, session.begin():
            membership = await self._membership_for_update(
                session, actor=actor, membership_id=membership_id
            )
            assignment = await self._create_assignment(
                session,
                actor=actor,
                membership=membership,
                input_value=input_value,
            )
            _bump_access_version(membership)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.assignment.created",
                actor=actor,
                target_type="role_assignment",
                target_id=assignment.id,
                after={"membership_id": str(membership.id), "scope": assignment.scope.value},
            )
        return await self.assignment_view(actor=actor, assignment_id=assignment.id)

    async def update_assignment(
        self,
        *,
        actor: BookingActor,
        assignment_id: UUID,
        input_value: RoleAssignmentInput,
    ) -> dict[str, Any]:
        """Change a role assignment scope only after authorizing both old and new scope."""

        actor.require(PermissionCode.ACCESS_ROLES_ASSIGN)
        async with self._database.session() as session, session.begin():
            assignment = await session.scalar(
                sa.select(BookingRoleAssignment)
                .where(
                    BookingRoleAssignment.id == assignment_id,
                    BookingRoleAssignment.organization_id == actor.organization_id,
                    BookingRoleAssignment.is_active.is_(True),
                )
                .with_for_update()
            )
            if assignment is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            if input_value.role_id != assignment.role_id:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            membership = await session.get(
                BookingMembership,
                assignment.membership_id,
                with_for_update=True,
            )
            role = await session.get(BookingRole, assignment.role_id)
            if membership is None or role is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            await self._authorize_assignment_change(session, actor=actor, assignment=assignment)
            permission_codes = set(
                (
                    await session.scalars(
                        sa.select(BookingRolePermission.permission_code).where(
                            BookingRolePermission.role_id == role.id
                        )
                    )
                ).all()
            )
            permissions = tuple(PermissionCode(code) for code in permission_codes)
            _require_actor_can_grant(actor, permissions)
            _validate_assignment_scope(
                input_value=input_value,
                permissions=permissions,
                role=role,
                membership=membership,
            )
            await self._authorize_assignment_scope(
                session,
                actor=actor,
                input_value=input_value,
                role=role,
            )
            before = {
                "scope": assignment.scope.value,
                "branch_ids": [
                    str(value)
                    for value in (
                        await session.scalars(
                            sa.select(BookingRoleAssignmentBranch.branch_id).where(
                                BookingRoleAssignmentBranch.assignment_id == assignment.id
                            )
                        )
                    ).all()
                ],
            }
            assignment.scope = input_value.scope
            assignment.starts_at = input_value.starts_at
            assignment.ends_at = input_value.ends_at
            await session.execute(
                sa.delete(BookingRoleAssignmentBranch).where(
                    BookingRoleAssignmentBranch.assignment_id == assignment.id
                )
            )
            if input_value.scope is AccessScope.BRANCH:
                session.add_all(
                    BookingRoleAssignmentBranch(assignment_id=assignment.id, branch_id=branch_id)
                    for branch_id in input_value.branch_ids
                )
            _bump_access_version(membership)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.assignment.updated",
                actor=actor,
                target_type="role_assignment",
                target_id=assignment.id,
                before=before,
                after={
                    "scope": assignment.scope.value,
                    "branch_ids": [str(value) for value in input_value.branch_ids],
                },
            )
        return await self.assignment_view(actor=actor, assignment_id=assignment.id)

    async def assignment_view(self, *, actor: BookingActor, assignment_id: UUID) -> dict[str, Any]:
        """Return one assignment only to a role-assignment reader in the same tenant."""

        actor.require(PermissionCode.ACCESS_ROLES_VIEW)
        async with self._database.session() as session:
            assignment = await session.scalar(
                sa.select(BookingRoleAssignment).where(
                    BookingRoleAssignment.id == assignment_id,
                    BookingRoleAssignment.organization_id == actor.organization_id,
                )
            )
            if assignment is None:
                raise BookingDomainError(BookingErrorCode.RESOURCE_NOT_FOUND)
            await self._authorize_assignment_view(session, actor=actor, assignment=assignment)
            return await self._assignment_view(session, assignment=assignment)

    async def revoke_assignment(
        self,
        *,
        actor: BookingActor,
        assignment_id: UUID,
        reason: str | None,
    ) -> None:
        """Revoke an assignment, bump its membership version, and audit the access change."""

        actor.require(PermissionCode.ACCESS_ROLES_ASSIGN)
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            assignment = await session.scalar(
                sa.select(BookingRoleAssignment)
                .where(
                    BookingRoleAssignment.id == assignment_id,
                    BookingRoleAssignment.organization_id == actor.organization_id,
                )
                .with_for_update()
            )
            if assignment is None or not assignment.is_active:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            await self._authorize_assignment_change(session, actor=actor, assignment=assignment)
            membership = await session.get(
                BookingMembership, assignment.membership_id, with_for_update=True
            )
            if membership is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            role = await session.get(BookingRole, assignment.role_id)
            if role is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            if role.is_system and role.code == BuiltInRole.OWNER.value:
                await self._ensure_owner_retained(
                    session,
                    organization_id=actor.organization_id,
                    removed_assignment_id=assignment.id,
                )
            assignment.is_active = False
            assignment.revoked_at = now
            assignment.revoked_by = actor.subject_id
            assignment.revoke_reason = reason.strip()[:500] if reason and reason.strip() else None
            _bump_access_version(membership)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.assignment.revoked",
                actor=actor,
                target_type="role_assignment",
                target_id=assignment.id,
                reason=reason,
                before={"scope": assignment.scope.value, "membership_id": str(membership.id)},
            )

    async def deactivate_member(
        self,
        *,
        actor: BookingActor,
        membership_id: UUID,
        reason: str | None,
    ) -> None:
        """Deactivate a membership and invalidate every already-issued staff token."""

        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_MEMBERS_DEACTIVATE)
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            membership = await self._membership_for_update(
                session, actor=actor, membership_id=membership_id
            )
            if not membership.is_active:
                return
            await self._ensure_owner_retained(
                session,
                organization_id=actor.organization_id,
                removed_membership_id=membership.id,
            )
            membership.is_active = False
            membership.deactivated_at = now
            membership.deactivated_by = actor.subject_id
            membership.deactivation_reason = (
                reason.strip()[:500] if reason and reason.strip() else None
            )
            _bump_access_version(membership)
            await session.execute(
                sa.update(BookingRoleAssignment)
                .where(
                    BookingRoleAssignment.membership_id == membership.id,
                    BookingRoleAssignment.is_active.is_(True),
                )
                .values(
                    is_active=False,
                    revoked_at=now,
                    revoked_by=actor.subject_id,
                    revoke_reason="membership deactivated",
                )
            )
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.member.deactivated",
                actor=actor,
                target_type="membership",
                target_id=membership.id,
                reason=reason,
            )

    async def transfer_ownership(
        self,
        *,
        actor: BookingActor,
        target_membership_id: UUID,
        reason: str | None,
    ) -> None:
        """Atomically grant OWNER to a target membership and revoke prior ownership assignments."""

        AccessPolicy.require_organization(actor, PermissionCode.ORGANIZATION_OWNERSHIP_TRANSFER)
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            target = await self._membership_for_update(
                session,
                actor=actor,
                membership_id=target_membership_id,
            )
            if not target.is_active:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            owner_role = await session.scalar(
                sa.select(BookingRole).where(
                    BookingRole.organization_id.is_(None),
                    BookingRole.code == BuiltInRole.OWNER.value,
                    BookingRole.is_system.is_(True),
                    BookingRole.is_active.is_(True),
                )
            )
            if owner_role is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            owner_rows = await self._active_owner_rows(
                session,
                organization_id=actor.organization_id,
                now=now,
            )
            if not owner_rows:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            target_assignment = next(
                (assignment for assignment, membership in owner_rows if membership.id == target.id),
                None,
            )
            if target_assignment is None:
                target_assignment = BookingRoleAssignment(
                    organization_id=actor.organization_id,
                    membership_id=target.id,
                    role_id=owner_role.id,
                    scope=AccessScope.ORGANIZATION,
                    assigned_by=actor.subject_id,
                    is_active=True,
                )
                session.add(target_assignment)
                await session.flush()
                _bump_access_version(target)
            previous_owner_ids: list[str] = []
            bumped_memberships: set[UUID] = {target.id}
            for assignment, membership in owner_rows:
                if assignment.id == target_assignment.id:
                    continue
                assignment.is_active = False
                assignment.revoked_at = now
                assignment.revoked_by = actor.subject_id
                assignment.revoke_reason = "ownership transferred"
                previous_owner_ids.append(str(membership.id))
                if membership.id not in bumped_memberships:
                    _bump_access_version(membership)
                    bumped_memberships.add(membership.id)
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="organization.ownership.transferred",
                actor=actor,
                target_type="membership",
                target_id=target.id,
                reason=reason,
                before={"owner_membership_ids": previous_owner_ids},
                after={"owner_membership_id": str(target.id)},
            )

    async def revoke_bind_code(
        self,
        *,
        actor: BookingActor,
        bind_code_id: UUID,
        reason: str | None,
    ) -> None:
        """Revoke an unused Telegram bind code before it can create a staff binding."""

        actor.require(PermissionCode.ACCESS_BIND_CODES_REVOKE)
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            bind_code = await session.scalar(
                sa.select(StaffBindCode)
                .where(
                    StaffBindCode.id == bind_code_id,
                    StaffBindCode.organization_id == actor.organization_id,
                )
                .with_for_update()
            )
            if (
                bind_code is None
                or bind_code.used_at is not None
                or bind_code.revoked_at is not None
            ):
                raise BookingDomainError(BookingErrorCode.INVALID_BIND_CODE)
            if bind_code.membership_id is None:
                AccessPolicy.require_organization(actor, PermissionCode.ACCESS_BIND_CODES_REVOKE)
            else:
                await self._authorize_membership_bind_scope(
                    session,
                    actor=actor,
                    membership_id=bind_code.membership_id,
                )
            bind_code.revoked_at = now
            bind_code.revoked_by = actor.subject_id
            bind_code.revoke_reason = reason.strip()[:500] if reason and reason.strip() else None
            append_audit_event(
                session,
                organization_id=actor.organization_id,
                action_code="access.bind_code.revoked",
                actor=actor,
                target_type="staff_bind_code",
                target_id=bind_code.id,
                reason=reason,
            )

    async def list_bind_codes(
        self,
        *,
        actor: BookingActor,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[dict[str, Any], ...]:
        """List bind-code metadata only; the raw one-time secret is never recoverable."""

        if limit < 1 or limit > 100 or offset < 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        actor.require(PermissionCode.ACCESS_BIND_CODES_VIEW)
        visible_branches = AccessPolicy.branch_ids(actor, PermissionCode.ACCESS_BIND_CODES_VIEW)
        now = self._clock.now()
        async with self._database.session() as session:
            statement = (
                sa.select(StaffBindCode, BookingMembership.display_name)
                .outerjoin(BookingMembership, BookingMembership.id == StaffBindCode.membership_id)
                .where(StaffBindCode.organization_id == actor.organization_id)
            )
            if visible_branches is not None:
                if not visible_branches:
                    return ()
                statement = (
                    statement.join(
                        BookingRoleAssignment,
                        BookingRoleAssignment.membership_id == BookingMembership.id,
                    )
                    .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
                    .join(
                        BookingRoleAssignmentBranch,
                        BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
                    )
                    .where(
                        BookingRoleAssignment.organization_id == actor.organization_id,
                        BookingRoleAssignment.is_active.is_(True),
                        BookingRole.is_active.is_(True),
                        sa.or_(
                            BookingRole.organization_id.is_(None),
                            BookingRole.organization_id == actor.organization_id,
                        ),
                        BookingRoleAssignment.scope == AccessScope.BRANCH,
                        BookingRoleAssignmentBranch.branch_id.in_(visible_branches),
                        sa.or_(
                            BookingRoleAssignment.starts_at.is_(None),
                            BookingRoleAssignment.starts_at <= now,
                        ),
                        sa.or_(
                            BookingRoleAssignment.ends_at.is_(None),
                            BookingRoleAssignment.ends_at > now,
                        ),
                    )
                    .distinct()
                )
            rows = (
                await session.execute(
                    statement.order_by(StaffBindCode.created_at.desc(), StaffBindCode.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        return tuple(
            {
                "id": bind_code.id,
                "membership_id": bind_code.membership_id,
                "membership_display_name": display_name,
                "specialist_id": bind_code.specialist_id,
                "expires_at": bind_code.expires_at,
                "used_at": bind_code.used_at,
                "revoked_at": bind_code.revoked_at,
                "revoke_reason": bind_code.revoke_reason,
                "created_at": bind_code.created_at,
            }
            for bind_code, display_name in rows
        )

    async def list_audit(
        self,
        *,
        actor: BookingActor,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[dict[str, Any], ...]:
        """Read append-only audit rows filtered to the actor's organization/branch visibility."""

        if limit < 1 or limit > 100 or offset < 0:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        actor.require(PermissionCode.AUDIT_VIEW)
        visible_branches = AccessPolicy.branch_ids(actor, PermissionCode.AUDIT_VIEW)
        async with self._database.session() as session:
            statement = sa.select(BookingAuditLog).where(
                BookingAuditLog.organization_id == actor.organization_id
            )
            if visible_branches is not None:
                statement = statement.where(BookingAuditLog.branch_id.in_(visible_branches))
            rows = (
                await session.scalars(
                    statement.order_by(BookingAuditLog.created_at.desc(), BookingAuditLog.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        return tuple(
            {
                "id": row.id,
                "action_code": row.action_code,
                "branch_id": row.branch_id,
                "actor_type": row.actor_type.value,
                "actor_id": row.actor_id,
                "actor_membership_id": row.actor_membership_id,
                "source": row.source.value,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "reason": row.reason,
                "before": row.before_json,
                "after": row.after_json,
                "metadata": row.metadata_json,
                "request_id": row.request_id,
                "correlation_id": row.correlation_id,
                "task_id": row.task_id,
                "created_at": row.created_at,
            }
            for row in rows
        )

    async def _active_owner_rows(
        self,
        session: Any,
        *,
        organization_id: UUID,
        now: datetime,
    ) -> list[tuple[BookingRoleAssignment, BookingMembership]]:
        """Lock all effective OWNER assignments before an ownership-reducing mutation."""

        rows = await session.execute(
            sa.select(BookingRoleAssignment, BookingMembership)
            .join(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
            .join(BookingMembership, BookingMembership.id == BookingRoleAssignment.membership_id)
            .where(
                BookingRoleAssignment.organization_id == organization_id,
                BookingRoleAssignment.is_active.is_(True),
                BookingMembership.is_active.is_(True),
                BookingRole.is_system.is_(True),
                BookingRole.is_active.is_(True),
                BookingRole.code == BuiltInRole.OWNER.value,
                sa.or_(
                    BookingRoleAssignment.starts_at.is_(None),
                    BookingRoleAssignment.starts_at <= now,
                ),
                sa.or_(
                    BookingRoleAssignment.ends_at.is_(None),
                    BookingRoleAssignment.ends_at > now,
                ),
            )
            .with_for_update()
        )
        return list(rows.all())

    async def _ensure_owner_retained(
        self,
        session: Any,
        *,
        organization_id: UUID,
        removed_assignment_id: UUID | None = None,
        removed_membership_id: UUID | None = None,
    ) -> None:
        """Refuse any action that would leave a tenant without an active effective OWNER."""

        owner_rows = await self._active_owner_rows(
            session,
            organization_id=organization_id,
            now=self._clock.now(),
        )
        remaining_owner_memberships = {
            membership.id
            for assignment, membership in owner_rows
            if assignment.id != removed_assignment_id and membership.id != removed_membership_id
        }
        if not remaining_owner_memberships:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)

    async def _create_assignment(
        self,
        session: Any,
        *,
        actor: BookingActor,
        membership: BookingMembership,
        input_value: RoleAssignmentInput,
    ) -> BookingRoleAssignment:
        """Validate delegability, role scope compatibility, and branch tenancy before insert."""

        role = await self._role_for_assignment(session, actor=actor, role_id=input_value.role_id)
        permission_codes = set(
            (
                await session.scalars(
                    sa.select(BookingRolePermission.permission_code).where(
                        BookingRolePermission.role_id == role.id
                    )
                )
            ).all()
        )
        permissions = tuple(PermissionCode(code) for code in permission_codes)
        _require_actor_can_grant(actor, permissions)
        _validate_assignment_scope(
            input_value=input_value,
            permissions=permissions,
            role=role,
            membership=membership,
        )
        await self._authorize_assignment_scope(
            session,
            actor=actor,
            input_value=input_value,
            role=role,
        )
        assignment = BookingRoleAssignment(
            organization_id=actor.organization_id,
            membership_id=membership.id,
            role_id=role.id,
            scope=input_value.scope,
            starts_at=input_value.starts_at,
            ends_at=input_value.ends_at,
            assigned_by=actor.subject_id,
            is_active=True,
        )
        session.add(assignment)
        try:
            await session.flush()
        except IntegrityError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
        if input_value.scope is AccessScope.BRANCH:
            session.add_all(
                BookingRoleAssignmentBranch(assignment_id=assignment.id, branch_id=branch_id)
                for branch_id in input_value.branch_ids
            )
        return assignment

    async def _role_for_update(
        self,
        session: Any,
        *,
        actor: BookingActor,
        role_id: UUID,
    ) -> BookingRole:
        """Lock one role that is globally built-in or belongs to the actor's own tenant."""

        role = await session.scalar(
            sa.select(BookingRole)
            .where(
                BookingRole.id == role_id,
                sa.or_(
                    BookingRole.organization_id.is_(None),
                    BookingRole.organization_id == actor.organization_id,
                ),
            )
            .with_for_update()
        )
        if role is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return role

    async def _role_for_assignment(
        self,
        session: Any,
        *,
        actor: BookingActor,
        role_id: UUID,
    ) -> BookingRole:
        """Load an active role with no cross-tenant custom-role reference path."""

        role = await session.scalar(
            sa.select(BookingRole).where(
                BookingRole.id == role_id,
                BookingRole.is_active.is_(True),
                sa.or_(
                    BookingRole.organization_id.is_(None),
                    BookingRole.organization_id == actor.organization_id,
                ),
            )
        )
        if role is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return role

    async def _membership_for_update(
        self,
        session: Any,
        *,
        actor: BookingActor,
        membership_id: UUID,
    ) -> BookingMembership:
        """Lock one target membership inside the actor's tenant before an authorization mutation."""

        membership = await session.scalar(
            sa.select(BookingMembership)
            .where(
                BookingMembership.id == membership_id,
                BookingMembership.organization_id == actor.organization_id,
            )
            .with_for_update()
        )
        if membership is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return membership

    async def _authorize_assignment_scope(
        self,
        session: Any,
        *,
        actor: BookingActor,
        input_value: RoleAssignmentInput,
        role: BookingRole,
    ) -> None:
        """Ensure a caller cannot delegate outside its own access-assignment scope."""

        if input_value.scope is AccessScope.ORGANIZATION:
            AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_ASSIGN)
        elif input_value.scope is AccessScope.BRANCH:
            await _require_branch_ids(session, actor=actor, branch_ids=input_value.branch_ids)
            for branch_id in input_value.branch_ids:
                AccessPolicy.require_branch(actor, PermissionCode.ACCESS_ROLES_ASSIGN, branch_id)
        else:
            AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_ASSIGN)
        if (
            _is_branch_manager(actor)
            and role.is_system
            and role.code not in {code.value for code in SAFE_BRANCH_MANAGER_ROLE_CODES}
        ):
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)

    async def _authorize_assignment_change(
        self,
        session: Any,
        *,
        actor: BookingActor,
        assignment: BookingRoleAssignment,
    ) -> None:
        """Apply the same delegation rule when revoking an existing assignment."""

        role = await session.get(BookingRole, assignment.role_id)
        if role is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        branches = tuple(
            (
                await session.scalars(
                    sa.select(BookingRoleAssignmentBranch.branch_id).where(
                        BookingRoleAssignmentBranch.assignment_id == assignment.id
                    )
                )
            ).all()
        )
        await self._authorize_assignment_scope(
            session,
            actor=actor,
            input_value=RoleAssignmentInput(
                role_id=role.id,
                scope=assignment.scope,
                branch_ids=branches,
            ),
            role=role,
        )

    async def _authorize_assignment_view(
        self,
        session: Any,
        *,
        actor: BookingActor,
        assignment: BookingRoleAssignment,
    ) -> None:
        """Allow branch-scoped readers to inspect only assignments in all of their branches."""

        if assignment.scope is AccessScope.ORGANIZATION:
            AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_VIEW)
            return
        if assignment.scope is AccessScope.BRANCH:
            branches = tuple(
                (
                    await session.scalars(
                        sa.select(BookingRoleAssignmentBranch.branch_id).where(
                            BookingRoleAssignmentBranch.assignment_id == assignment.id
                        )
                    )
                ).all()
            )
            if not branches:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            for branch_id in branches:
                AccessPolicy.require_branch(actor, PermissionCode.ACCESS_ROLES_VIEW, branch_id)
            return
        AccessPolicy.require_organization(actor, PermissionCode.ACCESS_ROLES_VIEW)

    async def _authorize_membership_bind_scope(
        self,
        session: Any,
        *,
        actor: BookingActor,
        membership_id: UUID,
    ) -> None:
        """Allow a branch actor to revoke a bind code only for a membership it can administer."""

        assignments = (
            await session.scalars(
                sa.select(BookingRoleAssignment).where(
                    BookingRoleAssignment.membership_id == membership_id,
                    BookingRoleAssignment.organization_id == actor.organization_id,
                    BookingRoleAssignment.is_active.is_(True),
                )
            )
        ).all()
        if not assignments:
            AccessPolicy.require_organization(actor, PermissionCode.ACCESS_BIND_CODES_REVOKE)
            return
        for assignment in assignments:
            if assignment.scope is AccessScope.ORGANIZATION:
                AccessPolicy.require_organization(actor, PermissionCode.ACCESS_BIND_CODES_REVOKE)
                return
            branches = tuple(
                (
                    await session.scalars(
                        sa.select(BookingRoleAssignmentBranch.branch_id).where(
                            BookingRoleAssignmentBranch.assignment_id == assignment.id
                        )
                    )
                ).all()
            )
            for branch_id in branches:
                AccessPolicy.require_branch(
                    actor, PermissionCode.ACCESS_BIND_CODES_REVOKE, branch_id
                )

    async def _member_view(self, session: Any, *, membership: BookingMembership) -> dict[str, Any]:
        """Render normalized role assignments without leaking unrelated tenant data."""

        assignments = (
            await session.scalars(
                sa.select(BookingRoleAssignment)
                .where(BookingRoleAssignment.membership_id == membership.id)
                .order_by(BookingRoleAssignment.created_at, BookingRoleAssignment.id)
            )
        ).all()
        return {
            "id": membership.id,
            "subject_id": membership.subject_id,
            "specialist_id": membership.specialist_id,
            "display_name": membership.display_name,
            "is_active": membership.is_active,
            "access_version": membership.access_version,
            "assignments": [
                await self._assignment_view(session, assignment=assignment)
                for assignment in assignments
            ],
        }

    async def _member_views(
        self,
        session: Any,
        *,
        memberships: Sequence[BookingMembership],
        visible_branch_ids: frozenset[UUID] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Render a membership page from one assignment/role/branch query, never N+1."""

        if not memberships:
            return ()
        membership_ids = tuple(member.id for member in memberships)
        statement = (
            sa.select(
                BookingRoleAssignment,
                BookingRole.code,
                BookingRoleAssignmentBranch.branch_id,
            )
            .outerjoin(BookingRole, BookingRole.id == BookingRoleAssignment.role_id)
            .outerjoin(
                BookingRoleAssignmentBranch,
                BookingRoleAssignmentBranch.assignment_id == BookingRoleAssignment.id,
            )
            .where(BookingRoleAssignment.membership_id.in_(membership_ids))
        )
        if visible_branch_ids is not None:
            statement = statement.where(
                BookingRoleAssignment.scope == AccessScope.BRANCH,
                BookingRoleAssignmentBranch.branch_id.in_(visible_branch_ids),
            )
        rows = (
            await session.execute(
                statement.order_by(BookingRoleAssignment.created_at, BookingRoleAssignment.id)
            )
        ).all()
        assignments_by_member: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        assignment_views: dict[UUID, dict[str, Any]] = {}
        assignment_branches: dict[UUID, list[UUID]] = defaultdict(list)
        for assignment, role_code, branch_id in rows:
            item: dict[str, Any] | None = assignment_views.get(assignment.id)
            if item is None:
                item = {
                    "id": assignment.id,
                    "role_id": assignment.role_id,
                    "role_code": role_code or "deleted",
                    "scope": assignment.scope.value,
                    "branch_ids": [],
                    "is_active": assignment.is_active,
                    "starts_at": assignment.starts_at,
                    "ends_at": assignment.ends_at,
                    "revoked_at": assignment.revoked_at,
                    "revoke_reason": assignment.revoke_reason,
                }
                assignment_views[assignment.id] = item
                assignments_by_member[assignment.membership_id].append(item)
            if branch_id is not None:
                assignment_branches[assignment.id].append(branch_id)
        for assignment_id, item in assignment_views.items():
            item["branch_ids"] = assignment_branches[assignment_id]
        return tuple(
            {
                "id": membership.id,
                "subject_id": membership.subject_id,
                "specialist_id": membership.specialist_id,
                "display_name": membership.display_name,
                "is_active": membership.is_active,
                "access_version": membership.access_version,
                "assignments": assignments_by_member[membership.id],
            }
            for membership in memberships
        )

    async def _assignment_view(
        self,
        session: Any,
        *,
        assignment: BookingRoleAssignment,
    ) -> dict[str, Any]:
        """Render a normalized role assignment with its branch scope and revocation metadata."""

        role = await session.get(BookingRole, assignment.role_id)
        branches = (
            await session.scalars(
                sa.select(BookingRoleAssignmentBranch.branch_id).where(
                    BookingRoleAssignmentBranch.assignment_id == assignment.id
                )
            )
        ).all()
        return {
            "id": assignment.id,
            "role_id": assignment.role_id,
            "role_code": role.code if role is not None else "deleted",
            "scope": assignment.scope.value,
            "branch_ids": branches,
            "is_active": assignment.is_active,
            "starts_at": assignment.starts_at,
            "ends_at": assignment.ends_at,
            "revoked_at": assignment.revoked_at,
            "revoke_reason": assignment.revoke_reason,
        }


def _custom_role_code(value: str) -> str:
    """Normalize the tenant-local stable role code and keep built-in namespace reserved."""

    normalized = value.strip().upper()
    if (
        len(normalized) < 3
        or len(normalized) > 80
        or not normalized.replace("_", "").isalnum()
        or not normalized.startswith("CUSTOM_")
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return normalized


def _required_text(value: str, *, maximum: int) -> str:
    """Validate a non-empty bounded operator-provided label."""

    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return normalized


def _normalize_permission_codes(values: Sequence[str]) -> tuple[PermissionCode, ...]:
    """Reject unknown permission strings before they can be persisted into a custom role."""

    try:
        normalized = tuple(sorted({normalize_permission(value) for value in values}, key=str))
    except BookingDomainError:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from None
    if not normalized:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return normalized


def _require_actor_can_grant(actor: BookingActor, permissions: Sequence[PermissionCode]) -> None:
    """Prohibit privilege escalation: a user can only create/assign permissions they possess."""

    if any(not actor.has(permission) for permission in permissions):
        raise BookingDomainError(BookingErrorCode.FORBIDDEN)


def _validate_assignment_scope(
    *,
    input_value: RoleAssignmentInput,
    permissions: Sequence[PermissionCode],
    role: BookingRole,
    membership: BookingMembership,
) -> None:
    """Check universal scope compatibility for all permissions carried by one role assignment."""

    if (
        input_value.ends_at is not None
        and input_value.starts_at is not None
        and input_value.ends_at <= input_value.starts_at
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if input_value.scope is AccessScope.BRANCH and not input_value.branch_ids:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if input_value.scope is not AccessScope.BRANCH and input_value.branch_ids:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if input_value.scope is AccessScope.SELF and membership.specialist_id is None:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if (
        role.is_system
        and role.code in {BuiltInRole.OWNER.value, BuiltInRole.ADMIN.value}
        and input_value.scope is not AccessScope.ORGANIZATION
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    if (
        role.is_system
        and role.code == BuiltInRole.OWNER.value
        and (input_value.starts_at is not None or input_value.ends_at is not None)
    ):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    for permission in permissions:
        if input_value.scope not in PERMISSION_BY_CODE[permission].allowed_scopes:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)


async def _require_branch_ids(
    session: Any,
    *,
    actor: BookingActor,
    branch_ids: Sequence[UUID],
) -> None:
    """Verify all branch IDs belong to the current tenant before creating a scope mapping."""

    unique_ids = tuple(dict.fromkeys(branch_ids))
    if len(unique_ids) != len(branch_ids):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    found = set(
        (
            await session.scalars(
                sa.select(BookingBranch.id).where(
                    BookingBranch.organization_id == actor.organization_id,
                    BookingBranch.id.in_(unique_ids),
                )
            )
        ).all()
    )
    if found != set(unique_ids):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)


def _is_branch_manager(actor: BookingActor) -> bool:
    """Detect a branch-manager assignment without letting a display role carry authorization."""

    return any(
        grant.role_code == BuiltInRole.BRANCH_MANAGER.value for grant in actor.scoped_permissions
    )


def _bump_access_version(membership: BookingMembership) -> None:
    """Invalidate every staff session at the next request after a material access change."""

    membership.access_version += 1


def _role_view(role: BookingRole, permissions: Sequence[PermissionCode]) -> dict[str, Any]:
    """Return one role safely from a just-mutated transaction."""

    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": sorted(permission.value for permission in permissions),
    }
