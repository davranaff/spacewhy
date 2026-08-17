"""One aiogram Bot client per application with bounded network behavior."""

from __future__ import annotations

from math import ceil

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from aiohttp import ClientSession, ClientTimeout
from pydantic import ValidationError as PydanticValidationError

from app.core.bots.contracts import (
    BotInlineButton,
    BotMessageResult,
    BotProviderIdentity,
    BotReplyButton,
    BotUpdate,
)
from app.core.bots.enums import BotProvider
from app.core.bots.ids import BotAppId
from app.infrastructure.bots.telegram.errors import (
    TelegramMalformedUpdateError,
    TelegramProviderFailureError,
    TelegramRecipientUnavailableError,
)
from app.infrastructure.bots.telegram.mapper import map_telegram_update


class BoundedAiohttpSession(AiohttpSession):
    """aiogram session with explicit total and TCP-connect timeout boundaries."""

    def __init__(self, *, request_timeout_seconds: float, connect_timeout_seconds: float) -> None:
        super().__init__(timeout=request_timeout_seconds)
        self._client_timeout = ClientTimeout(
            total=request_timeout_seconds,
            connect=connect_timeout_seconds,
        )

    async def create_session(self) -> ClientSession:
        """Create the aiohttp session once with the configured connection timeout."""

        if self._should_reset_connector:
            await self.close()
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                connector=self._connector_type(**self._connector_init),
                timeout=self._client_timeout,
            )
            self._should_reset_connector = False
        return self._session


class TelegramBotClient:
    """A single credential-bound aiogram client exposed only as a scoped gateway."""

    def __init__(
        self,
        *,
        app_id: BotAppId,
        bot: Bot,
        request_timeout_seconds: float,
    ) -> None:
        self._app_id = app_id
        self._bot = bot
        self._request_timeout_seconds = request_timeout_seconds
        self._closed = False

    @property
    def app_id(self) -> BotAppId:
        """Return the one app ID bound to this underlying credential."""

        return self._app_id

    @property
    def provider(self) -> BotProvider:
        """Return Telegram without allowing provider re-selection."""

        return BotProvider.TELEGRAM

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        *,
        inline_keyboard: tuple[tuple[BotInlineButton, ...], ...] | None = None,
        reply_keyboard: tuple[tuple[BotReplyButton, ...], ...] | None = None,
    ) -> BotMessageResult:
        """Send a text message and only compact app-owned keyboard payloads."""

        if (
            not recipient_id
            or len(text) > 4096
            or (inline_keyboard is not None and reply_keyboard is not None)
        ):
            raise TelegramProviderFailureError("Telegram outbound message is invalid.")
        markup = _reply_markup(inline_keyboard=inline_keyboard, reply_keyboard=reply_keyboard)
        try:
            message = await self._bot.send_message(
                chat_id=recipient_id,
                text=text,
                reply_markup=markup,
                request_timeout=ceil(self._request_timeout_seconds),
            )
        except TelegramForbiddenError as error:
            raise TelegramRecipientUnavailableError(
                "Telegram recipient cannot receive outbound messages."
            ) from error
        except TelegramAPIError as error:
            raise TelegramProviderFailureError("Telegram outbound message failed.") from error
        return BotMessageResult(provider_message_id=str(message.message_id))

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback through this same credential-bound bot client."""

        if not callback_id or (text is not None and len(text) > 200):
            raise TelegramProviderFailureError("Telegram callback response is invalid.")
        try:
            await self._bot.answer_callback_query(
                callback_query_id=callback_id,
                text=text,
                request_timeout=ceil(self._request_timeout_seconds),
            )
        except TelegramAPIError as error:
            raise TelegramProviderFailureError("Telegram callback response failed.") from error

    async def parse_update(self, payload: bytes) -> BotUpdate:
        """Use aiogram's typed parser and never retain the raw payload in runtime state."""

        try:
            update = Update.model_validate_json(payload)
        except PydanticValidationError as error:
            raise TelegramMalformedUpdateError("Telegram update payload is invalid.") from error
        return map_telegram_update(update)

    async def validate_identity(self) -> BotProviderIdentity:
        """Call Telegram getMe for only this bot token during optional startup validation."""

        try:
            identity = await self._bot.get_me(request_timeout=ceil(self._request_timeout_seconds))
        except TelegramAPIError as error:
            raise TelegramProviderFailureError("Telegram identity validation failed.") from error
        return BotProviderIdentity(provider_bot_id=identity.id, username=identity.username)

    async def close(self) -> None:
        """Close the aiogram session exactly once."""

        if self._closed:
            return
        self._closed = True
        await self._bot.session.close()


def _reply_markup(
    *,
    inline_keyboard: tuple[tuple[BotInlineButton, ...], ...] | None,
    reply_keyboard: tuple[tuple[BotReplyButton, ...], ...] | None,
) -> InlineKeyboardMarkup | ReplyKeyboardMarkup | None:
    """Translate neutral buttons only at the Telegram SDK boundary."""

    if inline_keyboard is not None:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=button.text, callback_data=button.callback_data)
                    for button in row
                ]
                for row in inline_keyboard
            ]
        )
    if reply_keyboard is not None:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=button.text, request_contact=button.request_contact)
                    for button in row
                ]
                for row in reply_keyboard
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    return None
