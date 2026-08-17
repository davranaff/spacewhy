"""The only normal production location that reads a raw Telegram token."""

from __future__ import annotations

from aiogram import Bot

from app.core.bots.contracts import BotProviderAdapter
from app.core.bots.errors import BotConfigurationError
from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotAppSettings
from app.infrastructure.bots.telegram.client import BoundedAiohttpSession, TelegramBotClient


class TelegramBotProviderFactory:
    """Create one isolated aiogram Bot and HTTP session per configured app."""

    def create(self, app_id: BotAppId, settings: BotAppSettings) -> BotProviderAdapter:
        """Resolve the secret once and immediately bind it to an opaque client."""

        if settings.token is None:
            raise BotConfigurationError(f"Bot app '{app_id}' has no token.")
        token = settings.token.get_secret_value()
        try:
            bot = Bot(
                token=token,
                session=BoundedAiohttpSession(
                    request_timeout_seconds=settings.request_timeout_seconds,
                    connect_timeout_seconds=settings.connect_timeout_seconds,
                ),
            )
        except ValueError as error:
            raise BotConfigurationError(f"Bot app '{app_id}' token is invalid.") from error
        return TelegramBotClient(
            app_id=app_id,
            bot=bot,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
