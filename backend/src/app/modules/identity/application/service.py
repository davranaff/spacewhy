"""Telegram enrollment, phone challenges, and shared session use cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from hmac import new
from uuid import UUID, uuid4

import sqlalchemy as sa

from app.core.bots.contracts import TelegramWebAppInitDataVerifier
from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode
from app.modules.identity.domain.phone import normalize_phone
from app.modules.identity.infrastructure.persistence.models import (
    AuthChallenge,
    IdentityAudit,
    Principal,
    SessionHandoff,
    TelegramBinding,
)
from app.modules.identity.infrastructure.security import (
    IdentityHandoffCodec,
    IdentityOtpCodec,
    IdentitySessionCodec,
)
from app.modules.identity.public import IdentityPrincipal, IdentitySession


@dataclass(frozen=True, slots=True)
class ChallengeDelivery:
    """Internal-only OTP delivery instruction; never serialized by HTTP schemas."""

    telegram_chat_id: str
    code: str


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    """Generic public challenge metadata plus an optional private delivery instruction."""

    id: UUID
    expires_at: datetime
    delivery: ChallengeDelivery | None


@dataclass(frozen=True, slots=True)
class HandoffResult:
    """Opaque one-time credential scoped to one SpaceDrop target."""

    token: str
    expires_at: datetime


class IdentityService:
    """Own identity state transitions and strict session issuance."""

    def __init__(
        self,
        *,
        database: Database,
        signing_secret: str,
        otp_ttl_seconds: int,
        otp_attempts: int,
        access_token_ttl_seconds: int,
        handoff_ttl_seconds: int,
        web_app_verifiers: Mapping[str, TelegramWebAppInitDataVerifier],
        webapp_max_age_seconds: int,
        clock: Clock | None = None,
    ) -> None:
        self._database = database
        self._secret = signing_secret.encode("utf-8")
        self._otp = IdentityOtpCodec(signing_secret)
        self._handoffs = IdentityHandoffCodec(signing_secret)
        self._sessions = IdentitySessionCodec(
            signing_secret=signing_secret,
            ttl_seconds=access_token_ttl_seconds,
        )
        self._otp_ttl_seconds = otp_ttl_seconds
        self._otp_attempts = otp_attempts
        self._handoff_ttl_seconds = handoff_ttl_seconds
        self._web_app_verifiers = web_app_verifiers
        self._webapp_max_age_seconds = webapp_max_age_seconds
        self._clock = clock or SystemClock()

    async def enroll_telegram_contact(
        self,
        *,
        bot_app_id: str,
        telegram_user_id: str | None,
        telegram_chat_id: str | None,
        contact_user_id: str | None,
        contact_phone: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        request_id: str | None,
    ) -> IdentityPrincipal:
        """Bind only the sender's own Telegram contact to one principal."""

        if (
            telegram_user_id is None
            or telegram_chat_id is None
            or contact_user_id != telegram_user_id
            or contact_phone is None
        ):
            raise IdentityDomainError(IdentityErrorCode.INVALID_TELEGRAM_CONTACT)
        phone = normalize_phone(contact_phone)
        now = self._clock.now()
        display_name = " ".join(part for part in (first_name, last_name) if part).strip() or None
        locale = _normalize_locale(language_code)
        async with self._database.session() as session, session.begin():
            await session.execute(
                sa.select(
                    sa.func.pg_advisory_xact_lock(sa.func.hashtext(f"identity:phone:{phone}"))
                )
            )
            phone_owner = await session.scalar(
                sa.select(TelegramBinding)
                .where(
                    TelegramBinding.normalized_phone == phone,
                    TelegramBinding.is_active.is_(True),
                )
                .with_for_update()
            )
            binding = await session.scalar(
                sa.select(TelegramBinding)
                .where(
                    TelegramBinding.bot_app_id == bot_app_id,
                    TelegramBinding.telegram_user_id == telegram_user_id,
                )
                .with_for_update()
            )
            if phone_owner is not None and (
                binding is None or phone_owner.principal_id != binding.principal_id
            ):
                raise IdentityDomainError(IdentityErrorCode.PHONE_ALREADY_BOUND)
            if binding is None:
                principal = Principal(display_name=display_name, locale=locale)
                session.add(principal)
                await session.flush()
                binding = TelegramBinding(
                    principal_id=principal.id,
                    bot_app_id=bot_app_id,
                    telegram_user_id=telegram_user_id,
                    telegram_chat_id=telegram_chat_id,
                    normalized_phone=phone,
                    verified_at=now,
                    is_active=True,
                )
                session.add(binding)
            else:
                principal = await session.get(Principal, binding.principal_id)
                if principal is None:
                    raise IdentityDomainError(IdentityErrorCode.INVALID_TELEGRAM_CONTACT)
                binding.telegram_chat_id = telegram_chat_id
                binding.normalized_phone = phone
                binding.verified_at = now
                binding.is_active = True
                principal.display_name = display_name or principal.display_name
                principal.locale = locale
                principal.is_active = True
            session.add(
                IdentityAudit(
                    principal_id=principal.id,
                    action="telegram_contact_enrolled",
                    request_id=request_id,
                    metadata_json={"bot_app_id": bot_app_id},
                )
            )
        return _public_principal(principal)

    async def create_phone_challenge(
        self,
        *,
        bot_app_id: str,
        phone: str,
        request_id: str | None,
    ) -> ChallengeResult:
        """Create an enumeration-safe challenge and return delivery data only internally."""

        normalized_phone = normalize_phone(phone)
        now = self._clock.now()
        challenge_id = uuid4()
        code = self._otp.code_for(challenge_id)
        phone_digest = new(self._secret, normalized_phone.encode(), sha256).hexdigest()
        async with self._database.session() as session, session.begin():
            recent_count = await session.scalar(
                sa.select(sa.func.count(AuthChallenge.id)).where(
                    AuthChallenge.phone_digest == phone_digest,
                    AuthChallenge.created_at >= now - timedelta(minutes=10),
                )
            )
            if int(recent_count or 0) >= 5:
                raise IdentityDomainError(IdentityErrorCode.RATE_LIMITED)
            binding = await session.scalar(
                sa.select(TelegramBinding).where(
                    TelegramBinding.bot_app_id == bot_app_id,
                    TelegramBinding.normalized_phone == normalized_phone,
                    TelegramBinding.is_active.is_(True),
                )
            )
            challenge = AuthChallenge(
                id=challenge_id,
                binding_id=binding.id if binding is not None else None,
                phone_digest=phone_digest,
                code_digest=self._otp.digest(challenge_id, code),
                attempts_remaining=self._otp_attempts,
                expires_at=now + timedelta(seconds=self._otp_ttl_seconds),
            )
            session.add(challenge)
            session.add(
                IdentityAudit(
                    principal_id=binding.principal_id if binding is not None else None,
                    action="phone_challenge_requested",
                    request_id=request_id,
                    metadata_json={"delivery_available": binding is not None},
                )
            )
        delivery = (
            ChallengeDelivery(telegram_chat_id=binding.telegram_chat_id, code=code)
            if binding is not None
            else None
        )
        return ChallengeResult(id=challenge_id, expires_at=challenge.expires_at, delivery=delivery)

    async def verify_phone_challenge(
        self,
        *,
        challenge_id: UUID,
        code: str,
        request_id: str | None,
    ) -> IdentitySession:
        """Consume one valid OTP atomically and issue a short-lived access session."""

        now = self._clock.now()
        failure: IdentityErrorCode | None = None
        principal: Principal | None = None
        async with self._database.session() as session, session.begin():
            challenge = await session.scalar(
                sa.select(AuthChallenge).where(AuthChallenge.id == challenge_id).with_for_update()
            )
            if (
                challenge is None
                or challenge.consumed_at is not None
                or challenge.expires_at <= now
                or challenge.binding_id is None
            ):
                raise IdentityDomainError(IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED)
            if challenge.attempts_remaining <= 0:
                raise IdentityDomainError(IdentityErrorCode.CHALLENGE_ATTEMPTS_EXHAUSTED)
            if not self._otp.verify(challenge.id, code, challenge.code_digest):
                challenge.attempts_remaining -= 1
                failure = (
                    IdentityErrorCode.CHALLENGE_ATTEMPTS_EXHAUSTED
                    if challenge.attempts_remaining <= 0
                    else IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED
                )
            else:
                binding = await session.scalar(
                    sa.select(TelegramBinding).where(
                        TelegramBinding.id == challenge.binding_id,
                        TelegramBinding.is_active.is_(True),
                    )
                )
                if binding is None:
                    raise IdentityDomainError(IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED)
                principal = await session.get(Principal, binding.principal_id)
                if principal is None or not principal.is_active:
                    raise IdentityDomainError(IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED)
                challenge.consumed_at = now
                session.add(
                    IdentityAudit(
                        principal_id=principal.id,
                        action="phone_challenge_verified",
                        request_id=request_id,
                        metadata_json={},
                    )
                )
        if failure is not None:
            raise IdentityDomainError(failure)
        if principal is None:
            raise IdentityDomainError(IdentityErrorCode.CHALLENGE_INVALID_OR_EXPIRED)
        public = _public_principal(principal)
        token, expires_at = self._sessions.issue(public, now=now)
        return IdentitySession(access_token=token, expires_at=expires_at, principal=public)

    async def authenticate_webapp(
        self,
        *,
        bot_app_id: str,
        init_data: str,
    ) -> IdentitySession:
        """Verify Telegram Mini App initData and resolve only a pre-enrolled principal."""

        verifier = self._web_app_verifiers.get(bot_app_id)
        if verifier is None:
            raise IdentityDomainError(IdentityErrorCode.INVALID_TELEGRAM_INIT_DATA)
        try:
            identity = verifier.verify_init_data(
                init_data,
                max_age_seconds=self._webapp_max_age_seconds,
                now=self._clock.now(),
            )
        except ValueError as error:
            raise IdentityDomainError(IdentityErrorCode.INVALID_TELEGRAM_INIT_DATA) from error
        async with self._database.session() as session:
            binding = await session.scalar(
                sa.select(TelegramBinding).where(
                    TelegramBinding.bot_app_id == bot_app_id,
                    TelegramBinding.telegram_user_id == identity.user_id,
                    TelegramBinding.is_active.is_(True),
                )
            )
            if binding is None:
                raise IdentityDomainError(IdentityErrorCode.ENROLLMENT_REQUIRED)
            principal = await session.get(Principal, binding.principal_id)
            if principal is None or not principal.is_active:
                raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID)
        public = _public_principal(principal)
        token, expires_at = self._sessions.issue(public, now=self._clock.now())
        return IdentitySession(access_token=token, expires_at=expires_at, principal=public)

    async def principal_from_session_token(self, token: str) -> IdentityPrincipal:
        """Verify the bearer token and reload current principal status."""

        try:
            claims = self._sessions.verify(token, now=self._clock.now())
        except (ValueError, TypeError) as error:
            raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID) from error
        async with self._database.session() as session:
            principal = await session.get(Principal, claims.principal_id)
        if principal is None or not principal.is_active:
            raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID)
        return _public_principal(principal)

    async def create_session_handoff(
        self,
        *,
        principal: IdentityPrincipal,
        target: str,
        request_id: str | None,
    ) -> HandoffResult:
        """Issue a short-lived opaque credential for one independent SpaceDrop."""

        _validate_handoff_target(target)
        now = self._clock.now()
        expires_at = now + timedelta(seconds=self._handoff_ttl_seconds)
        token = self._handoffs.issue_token()
        async with self._database.session() as session, session.begin():
            current = await session.get(Principal, principal.id)
            if current is None or not current.is_active:
                raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID)
            session.add(
                SessionHandoff(
                    principal_id=current.id,
                    target=target,
                    token_digest=self._handoffs.digest(token),
                    expires_at=expires_at,
                )
            )
            session.add(
                IdentityAudit(
                    principal_id=current.id,
                    action="session_handoff_created",
                    request_id=request_id,
                    metadata_json={"target": target},
                )
            )
        return HandoffResult(token=token, expires_at=expires_at)

    async def exchange_session_handoff(
        self,
        *,
        token: str,
        target: str,
        request_id: str | None,
    ) -> IdentitySession:
        """Consume one target-bound handoff atomically and issue a normal session."""

        _validate_handoff_target(target)
        now = self._clock.now()
        try:
            token_digest = self._handoffs.digest(token)
        except ValueError as error:
            raise IdentityDomainError(IdentityErrorCode.HANDOFF_INVALID_OR_EXPIRED) from error
        principal: Principal | None = None
        async with self._database.session() as session, session.begin():
            handoff = await session.scalar(
                sa.select(SessionHandoff)
                .where(
                    SessionHandoff.token_digest == token_digest,
                    SessionHandoff.target == target,
                )
                .with_for_update()
            )
            if handoff is None or handoff.consumed_at is not None or handoff.expires_at <= now:
                raise IdentityDomainError(IdentityErrorCode.HANDOFF_INVALID_OR_EXPIRED)
            principal = await session.get(Principal, handoff.principal_id)
            if principal is None or not principal.is_active:
                raise IdentityDomainError(IdentityErrorCode.HANDOFF_INVALID_OR_EXPIRED)
            handoff.consumed_at = now
            session.add(
                IdentityAudit(
                    principal_id=principal.id,
                    action="session_handoff_consumed",
                    request_id=request_id,
                    metadata_json={"target": target},
                )
            )
        public = _public_principal(principal)
        access_token, expires_at = self._sessions.issue(public, now=now)
        return IdentitySession(
            access_token=access_token,
            expires_at=expires_at,
            principal=public,
        )


def _normalize_locale(value: str | None) -> str:
    normalized = value.lower().split("-", maxsplit=1)[0] if value else "ru"
    return normalized if normalized in {"ru", "uz", "en"} else "ru"


def _validate_handoff_target(target: str) -> None:
    if target != "finance":
        raise IdentityDomainError(IdentityErrorCode.INVALID_REQUEST)


def _public_principal(principal: Principal) -> IdentityPrincipal:
    return IdentityPrincipal(
        id=principal.id,
        display_name=principal.display_name,
        locale=principal.locale,
    )
