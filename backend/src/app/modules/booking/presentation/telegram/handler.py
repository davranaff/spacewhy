"""Thin booking bot handler translating application instructions into scoped bot output."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.bots.context import BotUpdateContext
from app.core.bots.contracts import (
    BotInlineButton,
    BotReplyButton,
    BotUpdate,
    ScopedBotGateway,
)
from app.core.i18n.contracts import ScopedLocalizer
from app.core.i18n.locale import Locale
from app.modules.booking.application.telegram import BookingTelegramService, BotResponse
from app.modules.booking.domain.errors import BookingDomainError


@dataclass(slots=True)
class BookingTelegramHandler:
    """Map BookingTelegramService output to one pre-bound bot app and localizer only."""

    bot: ScopedBotGateway
    localizer: ScopedLocalizer
    service: BookingTelegramService

    async def handle(self, context: BotUpdateContext, update: BotUpdate) -> None:
        """Commit business work first, then acknowledge callbacks and send localized output."""

        try:
            response = await self.service.handle_update(
                bot_app_id=str(context.bot_app_id), update=update
            )
        except BookingDomainError as error:
            response = BotResponse(
                locale=str(context.locale),
                message_key=f"errors.{error.code.value.lower()}",
                params={},
            )
        if update.callback_id is not None:
            await self.bot.answer_callback(update.callback_id)
        if response is None or context.provider_chat_id is None:
            return
        locale = Locale.parse(response.locale)
        text = self.localizer.text(response.message_key, locale=locale, params=response.params)
        inline_keyboard = tuple(
            (
                BotInlineButton(
                    text=self.localizer.text(label_key, locale=locale, params=params),
                    callback_data=callback_data,
                ),
            )
            for label_key, callback_data, params in response.choices
        )
        reply_keyboard = (
            (
                (
                    BotReplyButton(
                        text=self.localizer.text("contact.share", locale=locale),
                        request_contact=True,
                    ),
                ),
            )
            if response.request_contact
            else None
        )
        await self.bot.send_message(
            context.provider_chat_id,
            text,
            inline_keyboard=inline_keyboard or None,
            reply_keyboard=reply_keyboard,
        )
