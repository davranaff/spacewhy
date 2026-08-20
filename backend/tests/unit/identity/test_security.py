"""Identity OTP and session cryptography tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.identity.infrastructure.security import (
    IdentityHandoffCodec,
    IdentityOtpCodec,
    IdentitySessionCodec,
)
from app.modules.identity.public import IdentityPrincipal

_SECRET = "test-identity-signing-secret-at-least-32-bytes"


def test_otp_is_deterministic_and_digest_verification_is_scoped() -> None:
    codec = IdentityOtpCodec(_SECRET)
    challenge_id = uuid4()

    code = codec.code_for(challenge_id)
    digest = codec.digest(challenge_id, code)

    assert len(code) == 6
    assert code.isdigit()
    assert codec.verify(challenge_id, code, digest)
    assert not codec.verify(uuid4(), code, digest)


def test_identity_session_round_trip_and_expiry() -> None:
    now = datetime(2026, 8, 20, 10, tzinfo=UTC)
    principal = IdentityPrincipal(id=uuid4(), display_name="Muxammad", locale="ru")
    codec = IdentitySessionCodec(signing_secret=_SECRET, ttl_seconds=900)

    token, expires_at = codec.issue(principal, now=now)
    claims = codec.verify(token, now=now + timedelta(minutes=1))

    assert claims.principal_id == principal.id
    assert claims.expires_at == expires_at
    with pytest.raises(ValueError, match="expired"):
        codec.verify(token, now=expires_at)


def test_identity_session_rejects_tampering() -> None:
    now = datetime(2026, 8, 20, 10, tzinfo=UTC)
    principal = IdentityPrincipal(id=uuid4(), display_name=None, locale="uz")
    codec = IdentitySessionCodec(signing_secret=_SECRET, ttl_seconds=900)
    token, _ = codec.issue(principal, now=now)
    header, payload, signature = token.split(".")
    tampered_payload = f"A{payload[1:]}" if payload[0] != "A" else f"B{payload[1:]}"

    with pytest.raises(ValueError, match="invalid"):
        codec.verify(f"{header}.{tampered_payload}.{signature}", now=now)


def test_identity_handoff_tokens_are_opaque_and_digest_only() -> None:
    codec = IdentityHandoffCodec(_SECRET)

    first = codec.issue_token()
    second = codec.issue_token()

    assert first != second
    assert len(first) >= 32
    assert codec.digest(first) == codec.digest(first)
    assert codec.digest(first) != codec.digest(second)
