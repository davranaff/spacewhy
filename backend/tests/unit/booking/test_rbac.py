"""Pure high-value checks for live scoped booking RBAC boundaries."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest

from app.core.db.database import Database
from app.modules.booking.application.access import AccessPolicy, BookingAccessService
from app.modules.booking.application.access_management import BookingAccessManagementService
from app.modules.booking.application.analytics import resolve_analytics_access
from app.modules.booking.application.context import BookingActor, ScopedPermissionGrant
from app.modules.booking.application.dto import AppointmentResult
from app.modules.booking.application.permissions import (
    BUILTIN_ROLE_DEFINITIONS,
    PERMISSION_BY_CODE,
    PermissionCode,
)
from app.modules.booking.domain.enums import (
    AccessRole,
    AccessScope,
    ActorType,
    AppointmentStatus,
)
from app.modules.booking.domain.errors import BookingDomainError
from app.modules.booking.infrastructure.auth.session import BookingSessionCodec
from app.modules.booking.presentation.http.schemas import AppointmentResponse


def _actor(
    *,
    role: AccessRole,
    grants: tuple[ScopedPermissionGrant, ...],
    specialist_id: UUID | None = None,
    customer_id: UUID | None = None,
) -> BookingActor:
    """Build a materialized actor that follows the production live-grant path."""

    return BookingActor(
        organization_id=uuid4(),
        subject_id=uuid4(),
        role=role,
        permissions=frozenset(grant.code.value for grant in grants),
        actor_type=ActorType.STAFF if role is not AccessRole.CUSTOMER else ActorType.CUSTOMER,
        specialist_id=specialist_id,
        customer_id=customer_id,
        membership_id=uuid4() if role is not AccessRole.CUSTOMER else None,
        access_version=1 if role is not AccessRole.CUSTOMER else None,
        scoped_permissions=grants,
    )


def _appointment_result() -> AppointmentResult:
    """Build a compact payment-bearing result for transport-level field filtering tests."""

    return AppointmentResult(
        id=uuid4(),
        public_number="B-2026-0001",
        status=AppointmentStatus.CONFIRMED,
        branch_id=uuid4(),
        customer_id=uuid4(),
        specialist_id=uuid4(),
        service_id=uuid4(),
        starts_at=datetime(2026, 8, 17, 9, tzinfo=UTC),
        ends_at=datetime(2026, 8, 17, 10, tzinfo=UTC),
        service_name="Consultation",
        specialist_name="Specialist",
        duration_minutes=60,
        price=Decimal("100.00"),
        currency="USD",
        payment_status="partial",
        paid_amount=Decimal("25.00"),
        refundable_amount=Decimal("25.00"),
        requires_manual_refund=False,
    )


def test_permission_registry_and_builtin_role_templates_stay_closed_and_complete() -> None:
    """Every built-in permission remains registry-defined and all ten standard roles exist."""

    assert len(BUILTIN_ROLE_DEFINITIONS) == 10
    assert {definition.code.value for definition in BUILTIN_ROLE_DEFINITIONS} == {
        "OWNER",
        "ADMIN",
        "BRANCH_MANAGER",
        "RECEPTIONIST",
        "CASHIER",
        "SPECIALIST",
        "INVENTORY_MANAGER",
        "ACCOUNTANT",
        "ANALYST",
        "AUDITOR",
    }
    assert set(PERMISSION_BY_CODE) == set(PermissionCode)
    assert all(
        permission in PERMISSION_BY_CODE
        for definition in BUILTIN_ROLE_DEFINITIONS
        for permission in definition.permissions
    )


def test_scope_policy_does_not_promote_branch_or_self_grants() -> None:
    """A concrete branch/self assignment cannot read a sibling branch or another specialist."""

    branch_id = uuid4()
    other_branch_id = uuid4()
    specialist_id = uuid4()
    other_specialist_id = uuid4()
    branch_actor = _actor(
        role=AccessRole.BRANCH_MANAGER,
        grants=(
            ScopedPermissionGrant(
                PermissionCode.BOOKINGS_VIEW,
                AccessScope.BRANCH,
                frozenset({branch_id}),
            ),
        ),
    )
    self_actor = _actor(
        role=AccessRole.SPECIALIST,
        specialist_id=specialist_id,
        grants=(ScopedPermissionGrant(PermissionCode.BOOKINGS_VIEW, AccessScope.SELF),),
    )

    assert AccessPolicy.allows_branch(branch_actor, PermissionCode.BOOKINGS_VIEW, branch_id)
    assert not AccessPolicy.allows_branch(
        branch_actor, PermissionCode.BOOKINGS_VIEW, other_branch_id
    )
    assert AccessPolicy.allows_appointment(
        self_actor,
        PermissionCode.BOOKINGS_VIEW,
        branch_id=other_branch_id,
        specialist_id=specialist_id,
        customer_id=uuid4(),
    )
    assert not AccessPolicy.allows_appointment(
        self_actor,
        PermissionCode.BOOKINGS_VIEW,
        branch_id=branch_id,
        specialist_id=other_specialist_id,
        customer_id=uuid4(),
    )
    with pytest.raises(BookingDomainError):
        AccessPolicy.require_branch(branch_actor, PermissionCode.BOOKINGS_VIEW, other_branch_id)


def test_booking_session_carries_identity_only_not_authority_claims() -> None:
    """Role changes and revocation stay enforceable without a permission snapshot in JWTs."""

    actor = _actor(
        role=AccessRole.RECEPTIONIST,
        grants=(
            ScopedPermissionGrant(
                PermissionCode.BOOKINGS_VIEW,
                AccessScope.ORGANIZATION,
            ),
        ),
    )
    codec = BookingSessionCodec(signing_secret="a" * 32, token_ttl_seconds=300)
    now = datetime(2026, 8, 17, 12, tzinfo=UTC)
    token, _ = codec.issue(actor, now=now)
    payload_part = token.split(".")[1]
    payload = json.loads(base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)))

    assert "permissions" not in payload
    assert "role" not in payload
    assert payload["membership_id"] == str(actor.membership_id)
    assert payload["access_version"] == actor.access_version
    assert codec.verify(token, now=now).membership_id == actor.membership_id


def test_appointment_payment_fields_are_hidden_from_non_financial_staff() -> None:
    """Specialists can receive booking data without a payment balance or refund leakage."""

    specialist_actor = _actor(
        role=AccessRole.SPECIALIST,
        specialist_id=uuid4(),
        grants=(ScopedPermissionGrant(PermissionCode.BOOKINGS_VIEW, AccessScope.SELF),),
    )
    cashier_actor = _actor(
        role=AccessRole.CASHIER,
        grants=(
            ScopedPermissionGrant(PermissionCode.CASH_PAYMENTS_VIEW, AccessScope.ORGANIZATION),
        ),
    )
    result = _appointment_result()

    hidden = AppointmentResponse.from_result(result, actor=specialist_actor)
    visible = AppointmentResponse.from_result(result, actor=cashier_actor)

    assert hidden.payment_status is None
    assert hidden.paid_amount is None
    assert hidden.refundable_amount is None
    assert hidden.requires_manual_refund is None
    assert visible.paid_amount == Decimal("25.00")


def test_analytics_keeps_finance_scope_independent_from_booking_scope() -> None:
    """A grant in one branch cannot make finance data visible in another booking branch."""

    booking_branch_id = uuid4()
    finance_branch_id = uuid4()
    actor = _actor(
        role=AccessRole.ANALYST,
        grants=(
            ScopedPermissionGrant(
                PermissionCode.ANALYTICS_BOOKINGS_VIEW,
                AccessScope.BRANCH,
                frozenset({booking_branch_id}),
            ),
            ScopedPermissionGrant(
                PermissionCode.ANALYTICS_FINANCE_VIEW,
                AccessScope.BRANCH,
                frozenset({finance_branch_id}),
            ),
        ),
    )

    access = resolve_analytics_access(actor)

    assert access.booking is not None
    assert access.finance is not None
    assert access.booking.branch_ids == frozenset({booking_branch_id})
    assert access.finance.branch_ids == frozenset({finance_branch_id})


def test_worker_actor_has_only_its_named_operation_permissions() -> None:
    """A background worker cannot accidentally become a tenant-wide staff superuser."""

    access = BookingAccessService(database=cast(Database, object()))
    actor = access.system_actor(
        organization_id=uuid4(),
        task_id="hold-expiry:test",
        operation="hold_expiry",
        branch_ids=frozenset({uuid4()}),
    )

    assert actor.has(PermissionCode.BOOKINGS_UPDATE)
    assert not actor.has(PermissionCode.CASH_REFUNDS_CREATE)
    assert actor.grants_for(PermissionCode.BOOKINGS_UPDATE)[0].scope is AccessScope.BRANCH
    with pytest.raises(ValueError):
        access.system_actor(
            organization_id=uuid4(),
            task_id="unknown:test",
            operation="unknown",
        )


@pytest.mark.asyncio
async def test_access_me_keeps_scopes_separate_for_each_permission() -> None:
    """The UI snapshot must not collapse branch access for independent permission grants."""

    booking_branch = uuid4()
    finance_branch = uuid4()
    assignment_id = uuid4()
    actor = _actor(
        role=AccessRole.ANALYST,
        grants=(
            ScopedPermissionGrant(
                PermissionCode.ANALYTICS_BOOKINGS_VIEW,
                AccessScope.BRANCH,
                frozenset({booking_branch}),
                assignment_id,
                "ANALYST",
            ),
            ScopedPermissionGrant(
                PermissionCode.ANALYTICS_FINANCE_VIEW,
                AccessScope.BRANCH,
                frozenset({finance_branch}),
                assignment_id,
                "ANALYST",
            ),
        ),
    )

    snapshot = await BookingAccessManagementService(database=cast(Database, object())).my_access(
        actor=actor
    )

    assert snapshot["permission_scopes"][PermissionCode.ANALYTICS_BOOKINGS_VIEW.value] == [
        {"scope": "branch", "branch_ids": [booking_branch]}
    ]
    assert snapshot["permission_scopes"][PermissionCode.ANALYTICS_FINANCE_VIEW.value] == [
        {"scope": "branch", "branch_ids": [finance_branch]}
    ]
    assert snapshot["accessible_branch_ids"] == sorted([booking_branch, finance_branch], key=str)
