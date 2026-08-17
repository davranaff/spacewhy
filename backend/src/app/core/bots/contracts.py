"""Provider-neutral contracts exposed to bootstrap and module presentation code."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.core.bots.context import BotUpdateContext
from app.core.bots.enums import BotProvider
from app.core.bots.ids import BotAppId


@dataclass(frozen=True, slots=True)
class BotInlineButton:
    """Provider-neutral compact inline callback button owned by one bot app flow."""

    text: str
    callback_data: str


@dataclass(frozen=True, slots=True)
class BotReplyButton:
    """Provider-neutral reply-keyboard button with an optional current-user contact request."""

    text: str
    request_contact: bool = False


@dataclass(frozen=True, slots=True)
class BotUpdate:
    """A minimal provider-neutral inbound update without raw payload logging."""

    provider_update_id: str | None
    provider_user_id: str | None
    provider_chat_id: str | None
    provider_language_code: str | None
    event_type: str
    message_text: str | None = None
    callback_data: str | None = None
    callback_id: str | None = None
    contact_user_id: str | None = None
    contact_phone_number: str | None = None
    provider_first_name: str | None = None
    provider_last_name: str | None = None
    provider_username: str | None = None


@dataclass(frozen=True, slots=True)
class BotMessageResult:
    """Safe outbound-send result returned through a scoped gateway."""

    provider_message_id: str | None


@dataclass(frozen=True, slots=True)
class BotProviderIdentity:
    """Optional provider identity result used only at startup validation."""

    provider_bot_id: int
    username: str | None


@dataclass(frozen=True, slots=True)
class TelegramWebAppIdentity:
    """Verified Telegram WebApp subject with no trusted tenant or role claims."""

    user_id: str
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    auth_date: datetime


@runtime_checkable
class TelegramWebAppInitDataVerifier(Protocol):
    """A credential-bound verifier for official Telegram WebApp initData."""

    def verify_init_data(
        self,
        init_data: str,
        *,
        max_age_seconds: int,
        now: datetime,
    ) -> TelegramWebAppIdentity:
        """Validate a signed initData string and return only verified user values."""

        ...


class ScopedBotGateway(Protocol):
    """A bot client pre-bound to exactly one public bot application ID."""

    @property
    def app_id(self) -> BotAppId:
        """Return the only app this gateway can act as."""

        ...

    @property
    def provider(self) -> BotProvider:
        """Return the pre-bound provider."""

        ...

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        *,
        inline_keyboard: tuple[tuple[BotInlineButton, ...], ...] | None = None,
        reply_keyboard: tuple[tuple[BotReplyButton, ...], ...] | None = None,
    ) -> BotMessageResult:
        """Send plain text with optional provider-neutral keyboard primitives."""

        ...

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a compact callback through the one app-bound provider client."""

        ...


@runtime_checkable
class BotUpdateHandler(Protocol):
    """A module-owned handler bound to exactly one bot runtime."""

    async def handle(self, context: BotUpdateContext, update: BotUpdate) -> None:
        """Handle one already-verified provider-neutral update."""

        ...


class BotProviderAdapter(ScopedBotGateway, Protocol):
    """Infrastructure-only provider adapter for one isolated bot client."""

    async def parse_update(self, payload: bytes) -> BotUpdate:
        """Parse one provider payload without routing to another application."""

        ...

    async def validate_identity(self) -> BotProviderIdentity:
        """Call the provider identity endpoint for this one client."""

        ...

    async def close(self) -> None:
        """Release all resources owned by this one provider client."""

        ...
