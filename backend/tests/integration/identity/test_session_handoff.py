"""Real PostgreSQL verification for one-time SpaceDrop session handoffs."""

from __future__ import annotations

from uuid import uuid4

import pytest
import sqlalchemy as sa
from pydantic import SecretStr

from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode
from app.modules.identity.infrastructure.persistence.models import IdentityAudit, Principal
from app.modules.identity.public import IdentityPrincipal


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finance_handoff_is_target_bound_and_consumed_once(
    test_database_url: str,
) -> None:
    database = Database(DatabaseSettings(url=SecretStr(test_database_url)))
    database.initialize()
    principal_id = uuid4()
    principal = IdentityPrincipal(id=principal_id, display_name="Handoff QA", locale="ru")
    service = IdentityService(
        database=database,
        signing_secret="integration-handoff-secret-at-least-32-characters",
        otp_ttl_seconds=300,
        otp_attempts=5,
        access_token_ttl_seconds=900,
        handoff_ttl_seconds=60,
        web_app_verifiers={},
        webapp_max_age_seconds=600,
    )

    try:
        async with database.session() as session, session.begin():
            session.add(
                Principal(
                    id=principal_id,
                    display_name=principal.display_name,
                    locale=principal.locale,
                    is_active=True,
                )
            )

        handoff = await service.create_session_handoff(
            principal=principal,
            target="finance",
            request_id="integration-create",
        )
        session = await service.exchange_session_handoff(
            token=handoff.token,
            target="finance",
            request_id="integration-exchange",
        )

        assert session.principal == principal
        assert await service.principal_from_session_token(session.access_token) == principal

        with pytest.raises(IdentityDomainError) as replay:
            await service.exchange_session_handoff(
                token=handoff.token,
                target="finance",
                request_id="integration-replay",
            )

        assert replay.value.code is IdentityErrorCode.HANDOFF_INVALID_OR_EXPIRED
    finally:
        async with database.session() as session, session.begin():
            await session.execute(
                sa.delete(IdentityAudit).where(IdentityAudit.principal_id == principal_id)
            )
            await session.execute(sa.delete(Principal).where(Principal.id == principal_id))
        await database.dispose()
