"""Identity-owned OTP and access-session cryptography."""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, new
from typing import Any, cast
from uuid import UUID

from app.modules.identity.public import IdentityPrincipal

_ISSUER = "spacewhy.identity"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode_json(value: dict[str, object]) -> str:
    return _b64url(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _decode_json(value: str) -> dict[str, Any]:
    decoded: object = json.loads(_b64url_decode(value))
    if not isinstance(decoded, dict):
        raise ValueError("Session payload is invalid.")
    return cast(dict[str, Any], decoded)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware.")
    return value.astimezone(UTC)


class IdentityOtpCodec:
    """Derive a challenge code and compare only keyed digests."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("OTP secret is too short.")
        self._secret = secret.encode("utf-8")

    def code_for(self, challenge_id: UUID) -> str:
        digest = new(self._secret, f"otp:{challenge_id}".encode(), sha256).digest()
        return f"{int.from_bytes(digest[:8], 'big') % 1_000_000:06d}"

    def digest(self, challenge_id: UUID, code: str) -> str:
        return new(
            self._secret,
            f"verify:{challenge_id}:{code}".encode(),
            sha256,
        ).hexdigest()

    def verify(self, challenge_id: UUID, code: str, expected_digest: str) -> bool:
        return compare_digest(self.digest(challenge_id, code), expected_digest)


class IdentityHandoffCodec:
    """Create opaque one-time handoff tokens and persist only keyed digests."""

    def __init__(self, signing_secret: str) -> None:
        if len(signing_secret) < 32:
            raise ValueError("Handoff secret is too short.")
        self._secret = signing_secret.encode("utf-8")

    def issue_token(self) -> str:
        return secrets.token_urlsafe(32)

    def digest(self, token: str) -> str:
        if not token:
            raise ValueError("Handoff token is required.")
        return new(self._secret, f"handoff:{token}".encode(), sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class IdentitySessionClaims:
    principal_id: UUID
    expires_at: datetime


class IdentitySessionCodec:
    """Issue strict identity-only HS256 access tokens."""

    def __init__(self, *, signing_secret: str, ttl_seconds: int) -> None:
        if len(signing_secret) < 32 or ttl_seconds <= 0:
            raise ValueError("Identity session configuration is invalid.")
        self._secret = signing_secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue(self, principal: IdentityPrincipal, *, now: datetime) -> tuple[str, datetime]:
        issued_at = _aware(now)
        expires_at = issued_at + timedelta(seconds=self._ttl_seconds)
        header = _encode_json({"alg": "HS256", "typ": "JWT"})
        payload = _encode_json(
            {
                "iss": _ISSUER,
                "sub": str(principal.id),
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
            }
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        signature = _b64url(new(self._secret, signing_input, sha256).digest())
        return f"{header}.{payload}.{signature}", expires_at

    def verify(self, token: str, *, now: datetime) -> IdentitySessionClaims:
        parts = token.split(".")
        if len(parts) != 3 or any(not part for part in parts):
            raise ValueError("Identity session is invalid.")
        header_part, payload_part, signature_part = parts
        try:
            header = _decode_json(header_part)
            payload = _decode_json(payload_part)
            presented_signature = _b64url_decode(signature_part)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            raise ValueError("Identity session is invalid.") from error
        if header != {"alg": "HS256", "typ": "JWT"} or payload.get("iss") != _ISSUER:
            raise ValueError("Identity session is invalid.")
        expected = new(
            self._secret,
            f"{header_part}.{payload_part}".encode("ascii"),
            sha256,
        ).digest()
        if not compare_digest(expected, presented_signature):
            raise ValueError("Identity session is invalid.")
        subject = payload.get("sub")
        expiry = payload.get("exp")
        if not isinstance(subject, str) or not isinstance(expiry, int):
            raise ValueError("Identity session is invalid.")
        expires_at = datetime.fromtimestamp(expiry, tz=UTC)
        if _aware(now) >= expires_at:
            raise ValueError("Identity session is expired.")
        return IdentitySessionClaims(principal_id=UUID(subject), expires_at=expires_at)
