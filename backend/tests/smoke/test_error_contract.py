"""Problem Details smoke tests across expected and unexpected failures."""

import pytest
from fastapi import FastAPI

from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings
from app.core.errors.exceptions import NotFoundError
from tests.conftest import application_client


def _add_test_routes(app: FastAPI) -> None:
    """Add test-only failure routes without placing fake endpoints in the product app."""

    async def not_found() -> None:
        raise NotFoundError()

    async def validated(page_size: int) -> None:
        del page_size

    async def unexpected() -> None:
        raise RuntimeError("database_url=postgresql+asyncpg://user:password@localhost/private")

    app.add_api_route("/_test/not-found", not_found, methods=["GET"])
    app.add_api_route("/_test/validated", validated, methods=["GET"])
    app.add_api_route("/_test/unexpected", unexpected, methods=["GET"])


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_routing_error_uses_problem_details(test_settings: Settings) -> None:
    """An unmatched route uses application/problem+json and keeps the request ID."""

    app = create_app(test_settings)

    async with application_client(app) as client:
        response = await client.get("/not-a-route")

    body = response.json()
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert body["code"] == "ROUTE_NOT_FOUND"
    assert body["request_id"] == response.headers["x-request-id"]


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_application_and_validation_errors_share_problem_contract(
    test_settings: Settings,
) -> None:
    """Expected and request-shape failures use one stable error representation."""

    app = create_app(test_settings)
    _add_test_routes(app)

    async with application_client(app) as client:
        not_found_response = await client.get("/_test/not-found")
        validation_response = await client.get("/_test/validated", params={"page_size": "invalid"})

    assert not_found_response.status_code == 404
    assert not_found_response.json()["code"] == "RESOURCE_NOT_FOUND"
    assert validation_response.status_code == 422
    assert validation_response.json()["code"] == "INVALID_REQUEST"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_unknown_errors_are_sanitized(test_settings: Settings) -> None:
    """Unexpected exceptions never return raw database URLs or exception messages."""

    app = create_app(test_settings)
    _add_test_routes(app)

    async with application_client(app) as client:
        response = await client.get("/_test/unexpected")

    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred."
    assert "password" not in response.text
    assert "database_url" not in response.text
