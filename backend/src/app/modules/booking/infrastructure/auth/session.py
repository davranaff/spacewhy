"""Signed booking identity sessions; authorization is deliberately reloaded from PostgreSQL."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, new
from typing import Any, cast
from uuid import UUID

from app.modules.booking.application.context import BookingActor
from app.modules.booking.domain.enums import SessionPrincipal

_ISSUER = "spacewhy.booking"


@dataclass(frozen=True, slots=True)
class BookingSessionClaims:
    """Validated identity claims; neither role nor permission claims exist in this token."""

    subject_id: UUID
    organization_id: UUID
    principal: SessionPrincipal
    customer_id: UUID | None
    specialist_id: UUID | None
    membership_id: UUID | None
    access_version: int | None
    expires_at: datetime


class BookingSessionCodec:
    """Small HS256 JWT implementation with strict identity-only payload validation."""

    def __init__(self, *, signing_secret: str, token_ttl_seconds: int) -> None:
        """Accept material from the composition root, never from request input."""

        if len(signing_secret) < 32 or token_ttl_seconds <= 0:
            raise ValueError("Booking session codec configuration is invalid.")
        self._secret = signing_secret.encode("utf-8")
        self._ttl_seconds = token_ttl_seconds

    def issue(self, actor: BookingActor, *, now: datetime) -> tuple[str, datetime]:
        """Issue a session with only enough identity to live-revalidate the actor later."""

        now_utc = _require_aware(now)
        expires_at = now_utc + timedelta(seconds=self._ttl_seconds)
        principal = _principal_for_actor(actor)
        if principal is SessionPrincipal.CUSTOMER:
            if actor.customer_id is None:
                raise ValueError("Booking customer session has no customer identity.")
        elif actor.membership_id is None or actor.access_version is None:
            raise ValueError("Booking staff session has no live membership version.")
        header = _encode_json({"alg": "HS256", "typ": "JWT"})
        payload = _encode_json(
            {
                "iss": _ISSUER,
                "sub": str(actor.subject_id),
                "org": str(actor.organization_id),
                "principal": principal.value,
                "customer_id": str(actor.customer_id) if actor.customer_id is not None else None,
                "specialist_id": (
                    str(actor.specialist_id) if actor.specialist_id is not None else None
                ),
                "membership_id": (
                    str(actor.membership_id) if actor.membership_id is not None else None
                ),
                "access_version": actor.access_version,
                "iat": int(now_utc.timestamp()),
                "exp": int(expires_at.timestamp()),
            }
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        signature = _b64url(new(self._secret, signing_input, sha256).digest())
        return f"{header}.{payload}.{signature}", expires_at

    def verify(self, token: str, *, now: datetime) -> BookingSessionClaims:
        """Verify signature, issuer, identity claim shape, and bounded lifetime."""

        parts = token.split(".")
        if len(parts) != 3 or any(not part for part in parts):
            raise ValueError("Booking session token is invalid.")
        header_part, payload_part, signature_part = parts
        try:
            header = _decode_json(header_part)
            payload = _decode_json(payload_part)
            presented_signature = _b64url_decode(signature_part)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            raise ValueError("Booking session token is invalid.") from error
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Booking session token header is invalid.")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = new(self._secret, signing_input, sha256).digest()
        if not compare_digest(expected_signature, presented_signature):
            raise ValueError("Booking session token signature is invalid.")
        return _claims_from_payload(payload, now=_require_aware(now))


def _principal_for_actor(actor: BookingActor) -> SessionPrincipal:
    """Refuse to turn worker/platform identities into public booking bearer sessions."""

    if actor.is_client:
        return SessionPrincipal.CUSTOMER
    if actor.membership_id is not None:
        return SessionPrincipal.STAFF
    raise ValueError("Only verified client and staff actors can receive booking sessions.")


def _claims_from_payload(payload: dict[str, Any], *, now: datetime) -> BookingSessionClaims:
    """Validate all claims before UUID construction can leak malformed token details."""

    if payload.get("iss") != _ISSUER:
        raise ValueError("Booking session issuer is invalid.")
    subject_id = _uuid_claim(payload.get("sub"))
    organization_id = _uuid_claim(payload.get("org"))
    raw_principal = payload.get("principal")
    raw_expiry = payload.get("exp")
    if not isinstance(raw_principal, str) or not isinstance(raw_expiry, int):
        raise ValueError("Booking session claims are invalid.")
    try:
        principal = SessionPrincipal(raw_principal)
    except ValueError as error:
        raise ValueError("Booking session principal is invalid.") from error
    customer_id = _optional_uuid_claim(payload.get("customer_id"))
    specialist_id = _optional_uuid_claim(payload.get("specialist_id"))
    membership_id = _optional_uuid_claim(payload.get("membership_id"))
    raw_access_version = payload.get("access_version")
    access_version: int | None
    if raw_access_version is None:
        access_version = None
    elif isinstance(raw_access_version, int) and raw_access_version > 0:
        access_version = raw_access_version
    else:
        raise ValueError("Booking session access version is invalid.")
    if principal is SessionPrincipal.CUSTOMER:
        if customer_id is None or membership_id is not None or access_version is not None:
            raise ValueError("Booking customer session scope is invalid.")
    elif principal is SessionPrincipal.STAFF:
        if customer_id is not None or membership_id is None or access_version is None:
            raise ValueError("Booking staff session scope is invalid.")
    else:
        raise ValueError("Booking platform sessions use a separate internal boundary.")
    expires_at = datetime.fromtimestamp(raw_expiry, tz=UTC)
    if expires_at <= now:
        raise ValueError("Booking session has expired.")
    return BookingSessionClaims(
        subject_id=subject_id,
        organization_id=organization_id,
        principal=principal,
        customer_id=customer_id,
        specialist_id=specialist_id,
        membership_id=membership_id,
        access_version=access_version,
        expires_at=expires_at,
    )


def _uuid_claim(value: object) -> UUID:
    """Parse a mandatory compact UUID claim."""

    if not isinstance(value, str):
        raise ValueError("Booking session UUID claim is invalid.")
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError("Booking session UUID claim is invalid.") from error


def _optional_uuid_claim(value: object) -> UUID | None:
    """Parse a nullable compact UUID claim."""

    if value is None:
        return None
    return _uuid_claim(value)


def _require_aware(value: datetime) -> datetime:
    """Normalize an injected verification time before timestamp comparison."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Booking session time must be timezone-aware.")
    return value.astimezone(UTC)


def _encode_json(value: dict[str, object]) -> str:
    """Serialize stable compact JSON before URL-safe base64 encoding."""

    return _b64url(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _decode_json(value: str) -> dict[str, Any]:
    """Decode a JSON object and reject scalar or list token payloads."""

    parsed_value: object = json.loads(_b64url_decode(value))
    if not isinstance(parsed_value, dict):
        raise ValueError("Booking session JSON claim is invalid.")
    return cast(dict[str, Any], parsed_value)


def _b64url(value: bytes) -> str:
    """Encode without padding as required by compact JWT serialization."""

    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    """Decode padded URL-safe input while rejecting non-ASCII token segments."""

    if not value.isascii():
        raise ValueError("Booking session token encoding is invalid.")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
