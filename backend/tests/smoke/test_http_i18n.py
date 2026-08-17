"""HTTP locale middleware and delivery dependency smoke coverage."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI, Request

from app.api.dependencies.locale import get_request_locale
from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings
from tests.conftest import application_client


def _add_locale_probe(app: FastAPI) -> None:
    """Attach a test-only HTTP presentation route without adding business behavior."""

    async def locale_probe(request: Request) -> dict[str, str]:
        await asyncio.sleep(0.01)
        return {"locale": str(get_request_locale(request))}

    app.add_api_route("/_test/locale", locale_probe, methods=["GET"])


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_http_locale_uses_accept_language_and_sets_content_language(
    test_settings: Settings,
) -> None:
    """Transport hints resolve once in middleware and remain available to presentation code."""

    app = create_app(test_settings)
    _add_locale_probe(app)

    async with application_client(app) as client:
        ru_response = await client.get(
            "/_test/locale",
            headers={"accept-language": "fr-FR, ru-RU;q=0.9"},
        )
        default_response = await client.get(
            "/_test/locale",
            headers={"accept-language": "malformed value"},
        )

    assert ru_response.json() == {"locale": "ru"}
    assert ru_response.headers["content-language"] == "ru"
    assert default_response.json() == {"locale": "en"}
    assert default_response.headers["content-language"] == "en"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_concurrent_http_requests_do_not_mix_locale_context(test_settings: Settings) -> None:
    """Context variables reset per request rather than leaking locale across concurrent work."""

    app = create_app(test_settings)
    _add_locale_probe(app)

    async with application_client(app) as client:
        ru_response, uz_response = await asyncio.gather(
            client.get("/_test/locale", headers={"accept-language": "ru-RU"}),
            client.get("/_test/locale", headers={"accept-language": "uz-UZ"}),
        )

    assert ru_response.json() == {"locale": "ru"}
    assert uz_response.json() == {"locale": "uz"}
