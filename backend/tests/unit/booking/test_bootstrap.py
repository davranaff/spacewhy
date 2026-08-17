"""Booking composition and catalog-isolation coverage without external dependencies."""

from __future__ import annotations

import pytest

from app.bootstrap.app_factory import create_app
from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotAppSettings, BotsSettings
from app.core.config.settings import Settings
from app.core.i18n.locale import Locale


@pytest.mark.asyncio
async def test_booking_bot_registration_validates_its_catalogs_and_uses_its_override(
    test_settings: Settings,
) -> None:
    """A staged disabled booking app still proves registration and gettext isolation at startup."""

    app_id = BotAppId("booking_bot")
    settings = test_settings.model_copy(
        update={
            "bots": BotsSettings(
                apps={
                    app_id: BotAppSettings(
                        enabled=False,
                        default_locale=Locale("ru"),
                        supported_locales=frozenset({Locale("ru"), Locale("uz"), Locale("en")}),
                    )
                }
            )
        }
    )
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        assert app.state.container.localization.is_initialized
        localizer = app.state.container.localization.scoped_localizer(
            module_name="booking",
            translation_domain="booking",
            bot_app_id=app_id,
            bot_default_locale=Locale("ru"),
        )
        assert localizer.text("bot.welcome", locale=Locale("ru")) == (
            "Добро пожаловать в сервис записи. Выберите действие."
        )
