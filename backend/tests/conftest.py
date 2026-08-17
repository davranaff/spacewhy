"""Shared deterministic settings and ASGI test client helpers."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config.environment import Environment
from app.core.config.settings import (
    APISettings,
    AppSettings,
    LoggingSettings,
    ObservabilitySettings,
    Settings,
)


@pytest.fixture
def test_settings() -> Settings:
    """Return isolated settings that never connect to PostgreSQL during app assembly."""

    return Settings(
        app=AppSettings(
            environment=Environment.TEST,
            debug=False,
            verify_dependencies_on_startup=False,
        ),
        api=APISettings(
            title="Spacewhy API Test",
            description="Test API",
            docs_enabled=True,
            openapi_enabled=True,
        ),
        logging=LoggingSettings(level="INFO", json_logs=False),
        observability=ObservabilitySettings(enabled=False),
    )


@pytest.fixture
def test_database_url() -> str:
    """Require an explicitly provisioned PostgreSQL URL for integration verification."""

    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests.")
    return database_url


@asynccontextmanager
async def application_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    """Run the real lifespan around an in-process ASGI client."""

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
