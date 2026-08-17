"""Bot ownership declarations and startup validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from app.bootstrap.app_factory import create_app
from app.core.bots.contracts import BotProviderIdentity
from app.core.bots.errors import BotRegistrationError, BotRuntimeError
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar
from app.core.bots.settings import BotAppSettings, BotsSettings
from app.core.config.settings import Settings
from tests.fakes import (
    FakeBotProviderFactory,
    RecordingHandlerFactory,
    bot_bootstrap,
    write_module_catalogs,
)


def _enabled_bot() -> BotAppSettings:
    """Create one fake-only enabled app configuration."""

    return BotAppSettings(
        enabled=True,
        token=SecretStr("test-token-a"),
        webhook_secret=SecretStr("test_webhook_secret_a"),
    )


def test_registrar_rejects_duplicate_app_claims_and_is_immutable(tmp_path: Path) -> None:
    """One app ID can have exactly one registration, while one module may own many apps."""

    registrar = BotAppRegistrar()
    handler_factory = RecordingHandlerFactory()
    support_app = BotAppId("support_bot")
    registrar.register(
        owner_module="support",
        app_id=support_app,
        translation_domain="support",
        module_root=tmp_path,
        handler_factory=handler_factory,
    )
    with pytest.raises(BotRegistrationError, match="more than once"):
        registrar.register(
            owner_module="sales",
            app_id=support_app,
            translation_domain="sales",
            module_root=tmp_path,
            handler_factory=handler_factory,
        )
    registrar.register(
        owner_module="support",
        app_id=BotAppId("operator_bot"),
        translation_domain="support",
        module_root=tmp_path,
        handler_factory=handler_factory,
    )
    assert len(registrar.freeze()) == 2
    with pytest.raises(BotRegistrationError, match="immutable"):
        registrar.register(
            owner_module="support",
            app_id=BotAppId("late_bot"),
            translation_domain="support",
            module_root=tmp_path,
            handler_factory=handler_factory,
        )


@pytest.mark.asyncio
async def test_startup_rejects_enabled_app_without_module_owner(test_settings: Settings) -> None:
    """Environment configuration alone cannot create an active bot runtime."""

    settings = test_settings.model_copy(
        update={"bots": BotsSettings(apps={BotAppId("support_bot"): _enabled_bot()})}
    )
    app = create_app(settings, bot_provider_factory=FakeBotProviderFactory())

    with pytest.raises(BotRegistrationError, match="unregistered"):
        async with app.router.lifespan_context(app):
            pass


@pytest.mark.asyncio
async def test_startup_rejects_module_registration_for_unknown_app(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """A module cannot claim a runtime not declared in typed settings."""

    app_id = BotAppId("support_bot")
    module_root = tmp_path / "support"
    write_module_catalogs(module_root=module_root, app_id=app_id)
    app = create_app(
        test_settings,
        module_bot_bootstraps=(
            bot_bootstrap(
                owner_module="support",
                app_id=app_id,
                module_root=module_root,
                handler_factory=RecordingHandlerFactory(),
            ),
        ),
        bot_provider_factory=FakeBotProviderFactory(),
    )

    with pytest.raises(BotRegistrationError, match="not configured"):
        async with app.router.lifespan_context(app):
            pass


@pytest.mark.asyncio
async def test_disabled_unregistered_app_is_allowed_but_never_builds_a_runtime(
    test_settings: Settings,
) -> None:
    """Disabled settings may be staged before their module registration is deployed."""

    app_id = BotAppId("future_bot")
    settings = test_settings.model_copy(
        update={"bots": BotsSettings(apps={app_id: BotAppSettings(enabled=False)})}
    )
    factory = FakeBotProviderFactory()
    app = create_app(settings, bot_provider_factory=factory)

    async with app.router.lifespan_context(app):
        assert app.state.container.bot_platform.is_ready

    assert app_id not in factory.created


@pytest.mark.asyncio
async def test_startup_rejects_expected_identity_mismatch_and_closes_adapter(
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    """Configured identity assertions fail closed without leaking provider credentials."""

    app_id = BotAppId("support_bot")
    module_root = tmp_path / "support"
    write_module_catalogs(module_root=module_root, app_id=app_id)
    bot_settings = _enabled_bot().model_copy(
        update={
            "validate_identity_on_startup": True,
            "expected_bot_id": 42,
            "expected_username": "support_bot",
        }
    )
    settings = test_settings.model_copy(update={"bots": BotsSettings(apps={app_id: bot_settings})})
    factory = FakeBotProviderFactory(
        identities={
            app_id: BotProviderIdentity(provider_bot_id=7, username="unexpected_bot"),
        }
    )
    app = create_app(
        settings,
        module_bot_bootstraps=(
            bot_bootstrap(
                owner_module="support",
                app_id=app_id,
                module_root=module_root,
                handler_factory=RecordingHandlerFactory(),
            ),
        ),
        bot_provider_factory=factory,
    )

    with pytest.raises(BotRuntimeError, match="identity validation failed"):
        async with app.router.lifespan_context(app):
            pass

    assert factory.created[app_id].close_calls == 1
