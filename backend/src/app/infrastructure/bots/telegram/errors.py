"""Telegram adapter errors with no raw provider payloads or credentials."""

from app.core.bots.errors import BotMalformedUpdateError, BotProviderFailureError


class TelegramMalformedUpdateError(BotMalformedUpdateError):
    """Telegram sent an update that cannot be mapped to the core contract."""


class TelegramProviderFailureError(BotProviderFailureError):
    """Telegram SDK failed without exposing its raw response to the caller."""


class TelegramRecipientUnavailableError(TelegramProviderFailureError):
    """Telegram permanently rejects delivery to a chat that can no longer receive messages."""
