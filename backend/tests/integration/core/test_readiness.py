"""Real PostgreSQL readiness endpoint integration coverage."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.bootstrap.app_factory import create_app
from app.core.config.settings import DatabaseSettings, Settings
from tests.conftest import application_client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readiness_endpoint_checks_real_postgresql(
    test_database_url: str,
    test_settings: Settings,
) -> None:
    """The production adapter backs the HTTP readiness result with asyncpg."""

    settings = test_settings.model_copy(
        update={"database": DatabaseSettings(url=SecretStr(test_database_url))}
    )
    app = create_app(settings)

    async with application_client(app) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "bot_platform": "ok"},
    }
