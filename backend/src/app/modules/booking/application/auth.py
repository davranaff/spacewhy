"""Telegram WebApp authentication that derives tenant and authority server-side."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bots.contracts import TelegramWebAppIdentity, TelegramWebAppInitDataVerifier
from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.core.errors.exceptions import AuthenticationError
from app.modules.booking.application.access import BookingAccessService
from app.modules.booking.application.context import BookingActor
from app.modules.booking.domain.enums import AccessRole, ActorType, SessionPrincipal
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.infrastructure.auth.session import BookingSessionCodec
from app.modules.booking.infrastructure.persistence.models import (
    BookingAccessGrant,
    BookingRateLimitBucket,
    BookingTelegramBotInstallation,
    Customer,
    CustomerIdentity,
    StaffTelegramBinding,
)


@dataclass(frozen=True, slots=True)
class BookingAuthResult:
    """One signed booking API session plus its safely displayable actor scope."""

    access_token: str
    expires_at: datetime
    actor: BookingActor


class BookingAuthService:
    """Authenticate WebApp initData without accepting a tenant, role, or user ID from callers."""

    def __init__(
        self,
        *,
        database: Database,
        access: BookingAccessService,
        session_codec: BookingSessionCodec,
        web_app_verifiers: Mapping[str, TelegramWebAppInitDataVerifier],
        max_init_data_age_seconds: int,
        auth_rate_limit_requests: int,
        auth_rate_limit_window_seconds: int,
        clock: Clock | None = None,
    ) -> None:
        """Receive only pre-bound verifiers; modules never resolve bot credentials."""

        self._database = database
        self._access = access
        self._session_codec = session_codec
        self._web_app_verifiers = web_app_verifiers
        self._max_init_data_age_seconds = max_init_data_age_seconds
        self._auth_rate_limit_requests = auth_rate_limit_requests
        self._auth_rate_limit_window_seconds = auth_rate_limit_window_seconds
        self._clock = clock or SystemClock()

    async def authenticate_client(
        self,
        *,
        bot_app_id: str,
        init_data: str,
        rate_limit_key: str,
    ) -> BookingAuthResult:
        """Create or find a tenant-scoped customer identity and issue a client session."""

        await self._consume_auth_rate_limit(bot_app_id=bot_app_id, rate_limit_key=rate_limit_key)
        identity = self._verify(bot_app_id=bot_app_id, init_data=init_data)
        async with self._database.session() as session:
            async with session.begin():
                organization_id = await self._organization_id(
                    session,
                    bot_app_id=bot_app_id,
                )
                await self._lock_telegram_identity(
                    session,
                    organization_id=organization_id,
                    bot_app_id=bot_app_id,
                    telegram_user_id=identity.user_id,
                )
                customer = await self._customer_for_identity(
                    session,
                    organization_id=organization_id,
                    bot_app_id=bot_app_id,
                    telegram_user_id=identity.user_id,
                    first_name=identity.first_name,
                    last_name=identity.last_name,
                    username=identity.username,
                    language_code=identity.language_code,
                )
                actor = await self._actor_for_customer(
                    session,
                    organization_id=organization_id,
                    customer=customer,
                )
            token, expires_at = self._session_codec.issue(actor, now=self._clock.now())
        return BookingAuthResult(access_token=token, expires_at=expires_at, actor=actor)

    async def authenticate_staff(
        self,
        *,
        bot_app_id: str,
        init_data: str,
        rate_limit_key: str,
    ) -> BookingAuthResult:
        """Issue a staff session only for a current one-time-code Telegram binding."""

        await self._consume_auth_rate_limit(bot_app_id=bot_app_id, rate_limit_key=rate_limit_key)
        identity = self._verify(bot_app_id=bot_app_id, init_data=init_data)
        async with self._database.session() as session:
            async with session.begin():
                organization_id = await self._organization_id(
                    session,
                    bot_app_id=bot_app_id,
                )
                binding = await session.scalar(
                    sa.select(StaffTelegramBinding)
                    .where(
                        StaffTelegramBinding.organization_id == organization_id,
                        StaffTelegramBinding.bot_app_id == bot_app_id,
                        StaffTelegramBinding.telegram_user_id == identity.user_id,
                        StaffTelegramBinding.is_active.is_(True),
                    )
                    .with_for_update()
                )
                if binding is None:
                    raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
                actor = await self._access.actor_for_staff_binding(
                    organization_id=organization_id,
                    subject_id=(binding.specialist_id if binding.membership_id is None else None),
                    membership_id=binding.membership_id,
                    specialist_id=binding.specialist_id,
                )
                binding.membership_id = actor.membership_id
            token, expires_at = self._session_codec.issue(actor, now=self._clock.now())
        return BookingAuthResult(access_token=token, expires_at=expires_at, actor=actor)

    async def _consume_auth_rate_limit(
        self,
        *,
        bot_app_id: str,
        rate_limit_key: str,
    ) -> None:
        """Enforce a hashed-key PostgreSQL limit before expensive signature verification."""

        scope = f"booking_auth:{bot_app_id}"
        key_digest = sha256(rate_limit_key.encode("utf-8")).hexdigest()
        now = self._clock.now()
        async with self._database.session() as session, session.begin():
            lock_key = f"booking:rate_limit:{scope}:{key_digest}"
            await session.execute(
                sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key)))
            )
            bucket = await session.scalar(
                sa.select(BookingRateLimitBucket)
                .where(
                    BookingRateLimitBucket.scope == scope,
                    BookingRateLimitBucket.key_digest == key_digest,
                )
                .with_for_update()
            )
            if bucket is None:
                bucket = BookingRateLimitBucket(
                    scope=scope,
                    key_digest=key_digest,
                    window_started_at=now,
                    request_count=0,
                )
                session.add(bucket)
                await session.flush()
            if now - bucket.window_started_at >= timedelta(
                seconds=self._auth_rate_limit_window_seconds
            ):
                bucket.window_started_at = now
                bucket.request_count = 0
            if bucket.request_count >= self._auth_rate_limit_requests:
                raise BookingDomainError(BookingErrorCode.RATE_LIMITED)
            bucket.request_count += 1

    async def actor_from_session_token(self, token: str) -> BookingActor:
        """Verify identity token then rehydrate current database authority for this request."""

        try:
            claims = self._session_codec.verify(token, now=self._clock.now())
        except ValueError as error:
            raise AuthenticationError() from error
        if claims.principal is SessionPrincipal.CUSTOMER:
            return await self._access.resolve_client_actor(
                organization_id=claims.organization_id,
                subject_id=claims.subject_id,
                customer_id=claims.customer_id,
            )
        if claims.principal is SessionPrincipal.STAFF:
            return await self._access.resolve_staff_actor(
                organization_id=claims.organization_id,
                subject_id=claims.subject_id,
                membership_id=claims.membership_id,
                access_version=claims.access_version,
            )
        raise AuthenticationError()

    def _verify(
        self,
        *,
        bot_app_id: str,
        init_data: str,
    ) -> TelegramWebAppIdentity:
        """Use only an explicitly injected app-specific verifier."""

        verifier = self._web_app_verifiers.get(bot_app_id)
        if verifier is None:
            raise BookingDomainError(BookingErrorCode.INVALID_TELEGRAM_INIT_DATA)
        try:
            return verifier.verify_init_data(
                init_data,
                max_age_seconds=self._max_init_data_age_seconds,
                now=self._clock.now(),
            )
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_TELEGRAM_INIT_DATA) from error

    async def _organization_id(
        self,
        session: AsyncSession,
        *,
        bot_app_id: str,
    ) -> UUID:
        """Resolve an organization only from the server-owned bot installation table."""

        installation = await session.scalar(
            sa.select(BookingTelegramBotInstallation).where(
                BookingTelegramBotInstallation.bot_app_id == bot_app_id,
                BookingTelegramBotInstallation.is_active.is_(True),
            )
        )
        if installation is None:
            raise BookingDomainError(BookingErrorCode.INVALID_TELEGRAM_INIT_DATA)
        return installation.organization_id

    async def _lock_telegram_identity(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        bot_app_id: str,
        telegram_user_id: str,
    ) -> None:
        """Serialize first-seen identity creation without relying on process-local locks."""

        key = f"booking:telegram:{organization_id}:{bot_app_id}:{telegram_user_id}"
        await session.execute(sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(key))))

    async def _customer_for_identity(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        bot_app_id: str,
        telegram_user_id: str,
        first_name: str,
        last_name: str | None,
        username: str | None,
        language_code: str | None,
    ) -> Customer:
        """Find or create exactly one customer identity inside the resolved tenant."""

        customer_identity = await session.scalar(
            sa.select(CustomerIdentity).where(
                CustomerIdentity.organization_id == organization_id,
                CustomerIdentity.provider == "telegram",
                CustomerIdentity.bot_app_id == bot_app_id,
                CustomerIdentity.external_user_id == telegram_user_id,
            )
        )
        if customer_identity is not None:
            customer = await session.get(Customer, customer_identity.customer_id)
            if customer is None:
                raise BookingDomainError(BookingErrorCode.INVALID_TELEGRAM_INIT_DATA)
            return customer
        customer = Customer(
            organization_id=organization_id,
            first_name=first_name[:160],
            last_name=last_name[:160] if last_name is not None else None,
            locale=_normalize_locale(language_code),
        )
        session.add(customer)
        await session.flush()
        session.add(
            CustomerIdentity(
                organization_id=organization_id,
                customer_id=customer.id,
                provider="telegram",
                bot_app_id=bot_app_id,
                external_user_id=telegram_user_id,
                username=username[:64] if username is not None else None,
                metadata_json={},
            )
        )
        return customer

    async def _actor_for_customer(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        customer: Customer,
    ) -> BookingActor:
        """Materialize a fixed CUSTOMER_OWN actor without making the client a staff member."""

        grant = await session.scalar(
            sa.select(BookingAccessGrant.is_active).where(
                BookingAccessGrant.organization_id == organization_id,
                BookingAccessGrant.subject_id == customer.id,
                BookingAccessGrant.customer_id == customer.id,
            )
        )
        if customer.is_blocked:
            raise BookingDomainError(BookingErrorCode.CUSTOMER_BLOCKED)
        if grant is False:
            raise BookingDomainError(BookingErrorCode.FORBIDDEN)
        return BookingActor(
            organization_id=organization_id,
            subject_id=customer.id,
            role=AccessRole.CUSTOMER,
            permissions=frozenset(),
            actor_type=ActorType.CUSTOMER,
            customer_id=customer.id,
        )


def _normalize_locale(value: str | None) -> str:
    """Keep customer locale in the module-supported compact namespace."""

    normalized = value.lower().split("-", maxsplit=1)[0] if value else "ru"
    return normalized if normalized in {"ru", "uz", "en"} else "ru"
