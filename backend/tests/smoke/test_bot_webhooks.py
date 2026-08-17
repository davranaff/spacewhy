"""Smoke coverage for isolated fake bot runtimes and Telegram webhook delivery."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from app.bootstrap.app_factory import create_app
from app.core.bots.errors import BotProviderFailureError
from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotAppSettings, BotsSettings
from app.core.config.settings import Settings
from app.core.i18n.locale import Locale
from app.modules.registry import ModuleBotBootstrap
from tests.conftest import application_client
from tests.fakes import (
    FakeBotProviderFactory,
    RecordingHandlerFactory,
    bot_bootstrap,
    write_module_catalogs,
)

_DEFAULT_LOCALE = Locale("en")


def _enabled_bot(
    *,
    token: str,
    secret: str,
    default_locale: Locale = _DEFAULT_LOCALE,
    processing_timeout_seconds: float = 10.0,
) -> BotAppSettings:
    """Create fake-only valid app settings for webhook tests."""

    return BotAppSettings(
        enabled=True,
        token=SecretStr(token),
        webhook_secret=SecretStr(secret),
        default_locale=default_locale,
        supported_locales=frozenset({Locale("en"), Locale("ru"), Locale("uz")}),
        processing_timeout_seconds=processing_timeout_seconds,
    )


def _webhook_headers(secret: str) -> dict[str, str]:
    """Build only the official Telegram verification header and JSON content type."""

    return {
        "content-type": "application/json",
        "x-telegram-bot-api-secret-token": secret,
    }


def _payload(*, update_id: str, language_code: str | None = None) -> bytes:
    """Serialize a compact fake provider update without message text."""

    body: dict[str, str] = {
        "update_id": update_id,
        "user_id": f"user-{update_id}",
        "chat_id": f"chat-{update_id}",
    }
    if language_code is not None:
        body["language_code"] = language_code
    return json.dumps(body).encode("utf-8")


def _bot_test_app(
    *,
    test_settings: Settings,
    tmp_path: Path,
    apps: dict[BotAppId, BotAppSettings],
    handlers: dict[BotAppId, RecordingHandlerFactory],
    provider_factory: FakeBotProviderFactory,
    webhook_max_payload_bytes: int = 1_048_576,
) -> tuple[FastAPI, Settings]:
    """Create a test app whose module bootstraps receive only scoped capabilities."""

    module_root = tmp_path / "support"
    bootstraps: list[ModuleBotBootstrap] = []
    for app_id, handler_factory in handlers.items():
        write_module_catalogs(module_root=module_root, app_id=app_id)
        bootstraps.append(
            bot_bootstrap(
                owner_module="support",
                app_id=app_id,
                module_root=module_root,
                handler_factory=handler_factory,
            )
        )
    settings = test_settings.model_copy(
        update={
            "bots": BotsSettings(
                apps=apps,
                webhook_max_payload_bytes=webhook_max_payload_bytes,
            )
        }
    )
    return (
        create_app(
            settings,
            module_bot_bootstraps=tuple(bootstraps),
            bot_provider_factory=provider_factory,
        ),
        settings,
    )


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_each_webhook_reaches_only_its_own_isolated_handler_and_client(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Concurrent Bot A/B updates retain exact client, handler, and locale ownership."""

    support_app = BotAppId("support_bot")
    sales_app = BotAppId("sales_assistant")
    support_handler = RecordingHandlerFactory()
    sales_handler = RecordingHandlerFactory()
    fake_factory = FakeBotProviderFactory()
    app, _ = _bot_test_app(
        test_settings=test_settings,
        tmp_path=tmp_path,
        apps={
            support_app: _enabled_bot(
                token="test-token-a",
                secret="test_webhook_secret_a",
                default_locale=Locale("ru"),
            ),
            sales_app: _enabled_bot(
                token="test-token-b",
                secret="test_webhook_secret_b",
                default_locale=Locale("uz"),
            ),
        },
        handlers={support_app: support_handler, sales_app: sales_handler},
        provider_factory=fake_factory,
    )

    async with application_client(app) as client:
        support_response, sales_response = await asyncio.gather(
            client.post(
                f"/webhooks/telegram/{support_app}",
                content=_payload(update_id="support", language_code="ru-RU"),
                headers=_webhook_headers("test_webhook_secret_a"),
            ),
            client.post(
                f"/webhooks/telegram/{sales_app}",
                content=_payload(update_id="sales", language_code="uz-UZ"),
                headers=_webhook_headers("test_webhook_secret_b"),
            ),
        )
        assert support_response.status_code == 204
        assert sales_response.status_code == 204
        assert support_response.headers["x-request-id"]
        assert support_handler.dependencies is not None
        assert sales_handler.dependencies is not None
        assert support_handler.dependencies.bot.app_id == support_app
        assert sales_handler.dependencies.bot.app_id == sales_app
        assert support_handler.dependencies.bot is not sales_handler.dependencies.bot
        await support_handler.dependencies.bot.send_message("chat-support", "hello")
        await sales_handler.dependencies.bot.send_message("chat-sales", "hello")

    assert [context.bot_app_id for context, _ in support_handler.handler.received] == [support_app]
    assert [context.bot_app_id for context, _ in sales_handler.handler.received] == [sales_app]
    assert support_handler.handler.received[0][0].locale == "ru"
    assert sales_handler.handler.received[0][0].locale == "uz"
    assert fake_factory.created[support_app].sent_messages == [("chat-support", "hello")]
    assert fake_factory.created[sales_app].sent_messages == [("chat-sales", "hello")]
    assert fake_factory.created[support_app].close_calls == 1
    assert fake_factory.created[sales_app].close_calls == 1


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_invalid_secret_unknown_and_disabled_apps_never_invoke_a_handler(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Safe 404 outcomes do not disclose app existence or credential validity."""

    enabled_app = BotAppId("support_bot")
    disabled_app = BotAppId("disabled_bot")
    enabled_handler = RecordingHandlerFactory()
    disabled_handler = RecordingHandlerFactory()
    fake_factory = FakeBotProviderFactory()
    app, _ = _bot_test_app(
        test_settings=test_settings,
        tmp_path=tmp_path,
        apps={
            enabled_app: _enabled_bot(token="test-token-a", secret="test_webhook_secret_a"),
            disabled_app: BotAppSettings(enabled=False),
        },
        handlers={enabled_app: enabled_handler, disabled_app: disabled_handler},
        provider_factory=fake_factory,
    )

    async with application_client(app) as client:
        wrong_secret = await client.post(
            f"/webhooks/telegram/{enabled_app}",
            content=_payload(update_id="wrong"),
            headers=_webhook_headers("test_webhook_secret_wrong"),
        )
        unknown = await client.post(
            "/webhooks/telegram/unknown_bot",
            content=_payload(update_id="unknown"),
            headers=_webhook_headers("test_webhook_secret_a"),
        )
        disabled = await client.post(
            f"/webhooks/telegram/{disabled_app}",
            content=_payload(update_id="disabled"),
            headers=_webhook_headers("unused_secret_value"),
        )

    assert [wrong_secret.status_code, unknown.status_code, disabled.status_code] == [404, 404, 404]
    assert not enabled_handler.handler.received
    assert not disabled_handler.handler.received
    assert disabled_app not in fake_factory.created


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_webhook_rejects_invalid_content_type_bounded_body_and_malformed_payload(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Payload processing is bounded and malformed input reaches no module handler."""

    app_id = BotAppId("support_bot")
    handler = RecordingHandlerFactory()
    fake_factory = FakeBotProviderFactory()
    app, _ = _bot_test_app(
        test_settings=test_settings,
        tmp_path=tmp_path,
        apps={app_id: _enabled_bot(token="test-token-a", secret="test_webhook_secret_a")},
        handlers={app_id: handler},
        provider_factory=fake_factory,
        webhook_max_payload_bytes=1_024,
    )

    async with application_client(app) as client:
        invalid_content_type = await client.post(
            f"/webhooks/telegram/{app_id}",
            content=_payload(update_id="content-type"),
            headers={"content-type": "text/plain"},
        )
        oversized = await client.post(
            f"/webhooks/telegram/{app_id}",
            content=b"x" * 1_025,
            headers={
                **_webhook_headers("test_webhook_secret_a"),
                "content-length": "1025",
            },
        )
        malformed = await client.post(
            f"/webhooks/telegram/{app_id}",
            content=b"not-json",
            headers=_webhook_headers("test_webhook_secret_a"),
        )

    assert invalid_content_type.status_code == 415
    assert oversized.status_code == 413
    assert malformed.status_code == 400
    assert not handler.handler.received
    assert "test_webhook_secret_a" not in malformed.text


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_webhook_timeout_is_bounded_and_openapi_hides_route(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """A slow handler returns a safe timeout and private webhook paths stay undocumented."""

    app_id = BotAppId("support_bot")
    handler = RecordingHandlerFactory()
    handler.handler.delay_seconds = 0.05
    fake_factory = FakeBotProviderFactory()
    app, _ = _bot_test_app(
        test_settings=test_settings,
        tmp_path=tmp_path,
        apps={
            app_id: _enabled_bot(
                token="test-token-a",
                secret="test_webhook_secret_a",
                processing_timeout_seconds=0.01,
            )
        },
        handlers={app_id: handler},
        provider_factory=fake_factory,
    )

    async with application_client(app) as client:
        response = await client.post(
            f"/webhooks/telegram/{app_id}",
            content=_payload(update_id="slow"),
            headers=_webhook_headers("test_webhook_secret_a"),
        )

    assert response.status_code == 504
    assert f"/webhooks/telegram/{app_id}" not in app.openapi()["paths"]


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_partial_startup_failure_closes_already_created_clients(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Identity failure cleans up every partially initialized isolated client."""

    support_app = BotAppId("support_bot")
    sales_app = BotAppId("sales_assistant")
    support_handler = RecordingHandlerFactory()
    sales_handler = RecordingHandlerFactory()
    fake_factory = FakeBotProviderFactory(fail_for_app=sales_app)
    app, _ = _bot_test_app(
        test_settings=test_settings,
        tmp_path=tmp_path,
        apps={
            support_app: _enabled_bot(
                token="test-token-a",
                secret="test_webhook_secret_a",
            ),
            sales_app: _enabled_bot(
                token="test-token-b",
                secret="test_webhook_secret_b",
            ).model_copy(update={"validate_identity_on_startup": True}),
        },
        handlers={support_app: support_handler, sales_app: sales_handler},
        provider_factory=fake_factory,
    )

    with pytest.raises(BotProviderFailureError):
        async with app.router.lifespan_context(app):
            pass

    assert fake_factory.created[support_app].close_calls == 1
    assert fake_factory.created[sales_app].close_calls == 1
