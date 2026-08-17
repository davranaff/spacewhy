"""Liveness, readiness, and request ID smoke tests."""

import pytest

from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings
from app.core.db.database import Database
from app.core.http.middleware.request_id import is_valid_request_id
from tests.conftest import application_client


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_liveness_is_available_without_postgresql(test_settings: Settings) -> None:
    """Liveness reports process health and never triggers a database check."""

    app = create_app(test_settings)

    async with application_client(app) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-request-id"]


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_request_id_preserves_valid_values_and_replaces_unsafe_values(
    test_settings: Settings,
) -> None:
    """Response IDs are valid UUIDs regardless of hostile incoming header text."""

    app = create_app(test_settings)
    valid_request_id = "02cd8ed7-a998-41fc-8d8d-c59ea9987f18"

    async with application_client(app) as client:
        valid_response = await client.get(
            "/health/live",
            headers={"X-Request-ID": valid_request_id},
        )
        invalid_response = await client.get(
            "/health/live",
            headers={"X-Request-ID": "forged\nrequest-id"},
        )

    assert valid_response.headers["x-request-id"] == valid_request_id
    assert invalid_response.headers["x-request-id"] != "forged\nrequest-id"
    assert is_valid_request_id(invalid_response.headers["x-request-id"])


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_readiness_reports_database_success(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
) -> None:
    """Readiness exposes only an explicit healthy dependency status."""

    async def healthy(_database: Database) -> bool:
        return True

    monkeypatch.setattr(Database, "check_health", healthy)
    app = create_app(test_settings)

    async with application_client(app) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "bot_platform": "ok"},
    }


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_readiness_fails_safely_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
) -> None:
    """Readiness returns a deterministic 503 response without driver exception text."""

    async def unavailable(_database: Database) -> bool:
        return False

    monkeypatch.setattr(Database, "check_health", unavailable)
    app = create_app(test_settings)

    async with application_client(app) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "bot_platform": "ok"},
    }
    assert "postgresql" not in response.text
