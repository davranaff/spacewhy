"""Provider factory used only by bootstrap to construct isolated bot clients."""

from __future__ import annotations

from typing import Protocol

from app.core.bots.contracts import BotProviderAdapter
from app.core.bots.errors import BotConfigurationError
from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotAppSettings
from app.infrastructure.bots.telegram.factory import TelegramBotProviderFactory


class BotProviderFactory(Protocol):
    """Create one credential-bound provider adapter for one configured app."""

    def create(self, app_id: BotAppId, settings: BotAppSettings) -> BotProviderAdapter:
        """Build a provider adapter without exposing it to unrelated modules."""

        ...


class DefaultBotProviderFactory:
    """Select exactly one configured provider implementation per bot app."""

    def create(self, app_id: BotAppId, settings: BotAppSettings) -> BotProviderAdapter:
        """Delegate construction to the selected provider-specific factory."""

        if settings.provider.value == "telegram":
            return TelegramBotProviderFactory().create(app_id, settings)
        raise BotConfigurationError(f"Bot app '{app_id}' has an unsupported provider.")
