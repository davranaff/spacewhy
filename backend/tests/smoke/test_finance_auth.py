"""Finance endpoints deny unauthenticated callers before persistence access."""

import pytest

from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings
from tests.conftest import application_client


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_finance_accounts_require_identity_session(test_settings: Settings) -> None:
    app = create_app(test_settings)

    async with application_client(app) as client:
        response = await client.get("/api/v1/finance/accounts")

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
