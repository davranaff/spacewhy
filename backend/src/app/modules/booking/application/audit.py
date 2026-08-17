"""Append-only, actor-aware audit event writer shared by booking application services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.booking.application.context import BookingActor
from app.modules.booking.domain.enums import ActorType, AuditSource
from app.modules.booking.infrastructure.persistence.models import BookingAuditLog


def append_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    action_code: str,
    actor: BookingActor | None = None,
    actor_type: ActorType | None = None,
    actor_id: UUID | None = None,
    source: AuditSource | None = None,
    branch_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    reason: str | None = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """Append a fully attributed immutable audit row to the caller's open transaction."""

    session.add(
        BookingAuditLog(
            organization_id=organization_id,
            branch_id=branch_id,
            event_type=action_code[:80],
            action_code=action_code[:120],
            actor_type=actor.actor_type if actor is not None else actor_type or ActorType.SYSTEM,
            actor_id=actor.subject_id if actor is not None else actor_id,
            actor_membership_id=actor.membership_id if actor is not None else None,
            source=actor.audit_source if actor is not None else source or AuditSource.SYSTEM,
            target_type=target_type[:64] if target_type is not None else None,
            target_id=target_id,
            reason=reason.strip()[:500] if reason and reason.strip() else None,
            before_json=dict(before) if before is not None else None,
            after_json=dict(after) if after is not None else None,
            metadata_json=dict(metadata or {}),
            request_id=actor.request_id if actor is not None else None,
            correlation_id=actor.correlation_id if actor is not None else None,
            task_id=actor.task_id if actor is not None else None,
            ip_address=actor.ip_address if actor is not None else None,
            user_agent=actor.user_agent if actor is not None else None,
        )
    )
