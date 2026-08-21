"""Real PostgreSQL verification for Telegram deep-linked phone login."""

from __future__ import annotations

from uuid import uuid4

import pytest
import sqlalchemy as sa
from pydantic import SecretStr

from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.start_payload import parse_phone_challenge_start_parameter
from app.modules.identity.infrastructure.persistence.models import (
    AuthChallenge,
    IdentityAudit,
    Principal,
    TelegramBinding,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deep_link_claim_contact_and_otp_complete_one_session(
    test_database_url: str,
) -> None:
    database = Database(DatabaseSettings(url=SecretStr(test_database_url)))
    database.initialize()
    suffix = str(uuid4().int)[-7:]
    phone = f"+99890{suffix}"
    telegram_user_id = f"deep-link-user-{suffix}"
    telegram_chat_id = f"deep-link-chat-{suffix}"
    request_prefix = f"deep-link-{suffix}"
    service = IdentityService(
        database=database,
        signing_secret="integration-deep-link-secret-at-least-32-characters",
        otp_ttl_seconds=300,
        otp_attempts=5,
        access_token_ttl_seconds=900,
        handoff_ttl_seconds=60,
        web_app_verifiers={},
        webapp_max_age_seconds=600,
    )
    challenge_id = None
    principal_id = None

    try:
        challenge = await service.create_phone_challenge(
            bot_app_id="spacewhy_auth_bot",
            phone=phone,
            request_id=f"{request_prefix}-create",
        )
        challenge_id = challenge.id
        assert challenge.delivery is None
        assert (
            parse_phone_challenge_start_parameter(f"/start {challenge.start_parameter}")
            == challenge.id
        )

        delivery_before_contact = await service.claim_phone_challenge(
            challenge_id=challenge.id,
            bot_app_id="spacewhy_auth_bot",
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            request_id=f"{request_prefix}-claim",
        )
        assert delivery_before_contact is None

        enrollment = await service.enroll_telegram_contact(
            bot_app_id="spacewhy_auth_bot",
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            contact_user_id=telegram_user_id,
            contact_phone=phone,
            first_name="Deep",
            last_name="Link",
            language_code="ru",
            request_id=f"{request_prefix}-contact",
        )
        principal_id = enrollment.principal.id
        assert enrollment.delivery is not None
        assert enrollment.delivery.telegram_chat_id == telegram_chat_id

        session = await service.verify_phone_challenge(
            challenge_id=challenge.id,
            code=enrollment.delivery.code,
            request_id=f"{request_prefix}-verify",
        )
        assert session.principal == enrollment.principal
        assert (
            await service.principal_from_session_token(session.access_token) == enrollment.principal
        )
    finally:
        async with database.session() as session, session.begin():
            await session.execute(
                sa.delete(IdentityAudit).where(IdentityAudit.request_id.startswith(request_prefix))
            )
            if challenge_id is not None:
                await session.execute(
                    sa.delete(AuthChallenge).where(AuthChallenge.id == challenge_id)
                )
            if principal_id is not None:
                await session.execute(
                    sa.delete(TelegramBinding).where(TelegramBinding.principal_id == principal_id)
                )
                await session.execute(sa.delete(Principal).where(Principal.id == principal_id))
        await database.dispose()
