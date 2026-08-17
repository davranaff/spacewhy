"""HTTP-only dependency adapters for signed booking session scope."""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated

from fastapi import Depends, Header, Request

from app.bootstrap.container import get_container_from_app
from app.core.errors.exceptions import AuthenticationError
from app.modules.booking.application.context import BookingActor
from app.modules.booking.bootstrap import BookingModuleRuntime
from app.modules.booking.domain.enums import AccessRole, AuditSource
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode


def get_booking_runtime(request: Request) -> BookingModuleRuntime:
    """Return the module runtime constructed once by the global composition root."""

    return get_container_from_app(request.app).booking


async def get_booking_actor(
    request: Request,
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    authorization: Annotated[str | None, Header()] = None,
) -> BookingActor:
    """Decode only a standard Bearer session, never body/query actor claims."""

    if authorization is None:
        raise AuthenticationError()
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or separator != " " or not token:
        raise AuthenticationError()
    actor = await runtime.auth.actor_from_session_token(token)
    client_host = request.client.host if request.client is not None else None
    return replace(
        actor,
        audit_source=AuditSource.API,
        request_id=_bounded_header(request, "X-Request-ID"),
        correlation_id=_bounded_header(request, "X-Correlation-ID"),
        ip_address=client_host[:64] if client_host is not None else None,
        user_agent=_bounded_header(request, "User-Agent", limit=500),
    )


def get_client_actor(
    actor: Annotated[BookingActor, Depends(get_booking_actor)],
) -> BookingActor:
    """Limit the client namespace to a signed customer session."""

    if actor.role is not AccessRole.CUSTOMER or actor.customer_id is None:
        raise BookingDomainError(BookingErrorCode.FORBIDDEN)
    return actor


def get_staff_actor(
    actor: Annotated[BookingActor, Depends(get_booking_actor)],
) -> BookingActor:
    """Require a bound staff role before exposing the staff namespace."""

    if actor.role is AccessRole.CUSTOMER or actor.specialist_id is None:
        raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
    return actor


def get_backoffice_actor(
    actor: Annotated[BookingActor, Depends(get_booking_actor)],
) -> BookingActor:
    """Allow a non-client staff actor into admin routes; each use case checks its own permission."""

    if actor.role is AccessRole.CUSTOMER or actor.membership_id is None:
        raise BookingDomainError(BookingErrorCode.FORBIDDEN)
    return actor


def require_idempotency_key(
    value: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    """Require a bounded replay key for every booking mutation that has side effects."""

    if value is None or not value.strip() or len(value) > 128:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return value.strip()


def _bounded_header(request: Request, name: str, *, limit: int = 128) -> str | None:
    """Copy opaque request metadata only in bounded audit-safe form."""

    value = request.headers.get(name)
    return value[:limit] if value else None
