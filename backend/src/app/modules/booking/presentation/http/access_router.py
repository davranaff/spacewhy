"""Dedicated access-management HTTP boundary; it is separate from generic booking CRUD."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.booking.application.access_management import RoleAssignmentInput
from app.modules.booking.application.context import BookingActor
from app.modules.booking.bootstrap import BookingModuleRuntime
from app.modules.booking.presentation.http.dependencies import (
    get_backoffice_actor,
    get_booking_runtime,
)
from app.modules.booking.presentation.http.schemas import (
    AccessCreateMemberRequest,
    AccessCustomRoleCloneRequest,
    AccessCustomRolePatchRequest,
    AccessCustomRoleRequest,
    AccessDataResponse,
    AccessListResponse,
    AccessOwnershipTransferRequest,
    AccessReasonRequest,
    AccessRoleAssignmentRequest,
)

router = APIRouter(prefix="/access", tags=["booking-access"])


def _assignment_input(value: AccessRoleAssignmentRequest) -> RoleAssignmentInput:
    """Translate transport data into the immutable application input type."""

    return RoleAssignmentInput(
        role_id=value.role_id,
        scope=value.scope,
        branch_ids=tuple(value.branch_ids),
        starts_at=value.starts_at,
        ends_at=value.ends_at,
    )


@router.get(
    "/me", response_model=AccessDataResponse, summary="Get current effective booking access"
)
async def get_my_access(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Return only the live server-resolved grants for the authenticated staff membership."""

    return AccessDataResponse(data=await runtime.access_management.my_access(actor=actor))


@router.get("/permissions", response_model=AccessListResponse, summary="List permission registry")
async def list_permissions(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessListResponse:
    """Expose stable permission metadata for permission-aware management UI."""

    return AccessListResponse(
        items=list(await runtime.access_management.list_permissions(actor=actor))
    )


@router.get(
    "/roles", response_model=AccessListResponse, summary="List built-in and tenant custom roles"
)
async def list_roles(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessListResponse:
    """Return roles only in the signed actor's organization plus globally owned built-ins."""

    return AccessListResponse(items=list(await runtime.access_management.list_roles(actor=actor)))


@router.post(
    "/roles",
    response_model=AccessDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant custom role",
)
async def create_custom_role(
    payload: AccessCustomRoleRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Create a custom role only from permissions the signed actor can already delegate."""

    return AccessDataResponse(
        data=await runtime.access_management.create_custom_role(
            actor=actor,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            permission_codes=payload.permission_codes,
        )
    )


@router.patch("/roles/{role_id}", response_model=AccessDataResponse, summary="Update custom role")
async def update_custom_role(
    role_id: UUID,
    payload: AccessCustomRolePatchRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Update a tenant custom role while built-in role definitions remain source controlled."""

    return AccessDataResponse(
        data=await runtime.access_management.update_custom_role(
            actor=actor,
            role_id=role_id,
            name=payload.name,
            description=payload.description,
            permission_codes=payload.permission_codes,
        )
    )


@router.post(
    "/roles/{role_id}/clone",
    response_model=AccessDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a role into a tenant custom role",
)
async def clone_role(
    role_id: UUID,
    payload: AccessCustomRoleCloneRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Copy only permissions the caller currently holds; system roles remain immutable."""

    return AccessDataResponse(
        data=await runtime.access_management.clone_role(
            actor=actor,
            source_role_id=role_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
        )
    )


@router.post(
    "/roles/{role_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate an unused tenant custom role",
)
async def deactivate_custom_role(
    role_id: UUID,
    payload: AccessReasonRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """Immediately invalidate affected staff sessions while preserving the audit trail."""

    await runtime.access_management.deactivate_custom_role(
        actor=actor,
        role_id=role_id,
        reason=payload.reason,
    )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tenant custom role with no role assignments",
)
async def delete_custom_role(
    role_id: UUID,
    payload: AccessReasonRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """System roles and any role with assignment history cannot be deleted through this API."""

    await runtime.access_management.delete_custom_role(
        actor=actor,
        role_id=role_id,
        reason=payload.reason,
    )


@router.get("/members", response_model=AccessListResponse, summary="List scoped staff memberships")
async def list_members(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessListResponse:
    """List memberships under organization or branch scope without returning client identities."""

    return AccessListResponse(items=list(await runtime.access_management.list_members(actor=actor)))


@router.get(
    "/members/{membership_id}/access",
    response_model=AccessDataResponse,
    summary="Get one membership's live effective permissions",
)
async def get_member_access(
    membership_id: UUID,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Expose server-derived grants only when the viewer can see the target membership scope."""

    return AccessDataResponse(
        data=await runtime.access_management.member_access(
            actor=actor,
            membership_id=membership_id,
        )
    )


@router.post(
    "/members",
    response_model=AccessDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create staff membership with roles",
)
async def create_member(
    payload: AccessCreateMemberRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Create a membership and all initial assignments transactionally."""

    return AccessDataResponse(
        data=await runtime.access_management.create_member(
            actor=actor,
            subject_id=payload.subject_id,
            specialist_id=payload.specialist_id,
            display_name=payload.display_name,
            assignments=tuple(_assignment_input(item) for item in payload.assignments),
        )
    )


@router.post(
    "/members/{membership_id}/assignments",
    response_model=AccessDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign scoped role to membership",
)
async def assign_role(
    membership_id: UUID,
    payload: AccessRoleAssignmentRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """Add a role assignment and make existing staff bearer sessions stale immediately."""

    return AccessDataResponse(
        data=await runtime.access_management.assign_role(
            actor=actor,
            membership_id=membership_id,
            input_value=_assignment_input(payload),
        )
    )


@router.patch(
    "/assignments/{assignment_id}",
    response_model=AccessDataResponse,
    summary="Change an existing role assignment scope",
)
async def update_assignment(
    assignment_id: UUID,
    payload: AccessRoleAssignmentRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AccessDataResponse:
    """The role ID must match the existing assignment; only scope/window can change."""

    return AccessDataResponse(
        data=await runtime.access_management.update_assignment(
            actor=actor,
            assignment_id=assignment_id,
            input_value=_assignment_input(payload),
        )
    )


@router.post(
    "/assignments/{assignment_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke role assignment",
)
async def revoke_assignment(
    assignment_id: UUID,
    payload: AccessReasonRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """Revoke one assignment with actor/reason audit data and token-version invalidation."""

    await runtime.access_management.revoke_assignment(
        actor=actor,
        assignment_id=assignment_id,
        reason=payload.reason,
    )


@router.post(
    "/members/{membership_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate staff membership",
)
async def deactivate_member(
    membership_id: UUID,
    payload: AccessReasonRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """Deactivate a staff membership and revoke every active role assignment at once."""

    await runtime.access_management.deactivate_member(
        actor=actor,
        membership_id=membership_id,
        reason=payload.reason,
    )


@router.post(
    "/ownership/transfer",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Atomically transfer tenant ownership to an active membership",
)
async def transfer_ownership(
    payload: AccessOwnershipTransferRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """Only the ownership-transfer permission can invoke this protected tenant-only workflow."""

    await runtime.access_management.transfer_ownership(
        actor=actor,
        target_membership_id=payload.membership_id,
        reason=payload.reason,
    )


@router.post(
    "/bind-codes/{bind_code_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke unused Telegram bind code",
)
async def revoke_bind_code(
    bind_code_id: UUID,
    payload: AccessReasonRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> None:
    """Prevent a not-yet-used code from binding a Telegram account to staff authority."""

    await runtime.access_management.revoke_bind_code(
        actor=actor,
        bind_code_id=bind_code_id,
        reason=payload.reason,
    )


@router.get(
    "/bind-codes",
    response_model=AccessListResponse,
    summary="List scoped bind-code metadata",
)
async def list_bind_codes(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccessListResponse:
    """List expiring/used/revoked codes without ever returning their stored digest or raw secret."""

    return AccessListResponse(
        items=list(
            await runtime.access_management.list_bind_codes(
                actor=actor,
                limit=limit,
                offset=offset,
            )
        )
    )


@router.get("/audit", response_model=AccessListResponse, summary="Read scoped access audit log")
async def list_audit(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccessListResponse:
    """Read append-only audit rows only within current organization/branch scope."""

    return AccessListResponse(
        items=list(
            await runtime.access_management.list_audit(actor=actor, limit=limit, offset=offset)
        )
    )
