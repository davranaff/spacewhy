"""Thin Telegram contact-enrollment handler."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.bots.context import BotUpdateContext
from app.core.bots.contracts import BotReplyButton, BotUpdate, ScopedBotGateway
from app.core.i18n.contracts import ScopedLocalizer
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.errors import IdentityDomainError


@dataclass(slots=True)
class IdentityTelegramHandler:
    """Request a native contact and pass verified input to Identity."""

    bot: ScopedBotGateway
    localizer: ScopedLocalizer
    service: IdentityService

    async def handle(self, context: BotUpdateContext, update: BotUpdate) -> None:
        if context.provider_chat_id is None:
            return
        locale = context.locale
        if update.contact_phone_number is None:
            await self.bot.send_message(
                context.provider_chat_id,
                self.localizer.text("enrollment.request", locale=locale),
                reply_keyboard=(
                    (
                        BotReplyButton(
                            text=self.localizer.text("enrollment.share_contact", locale=locale),
                            request_contact=True,
                        ),
                    ),
                ),
            )
            return
        try:
            await self.service.enroll_telegram_contact(
                bot_app_id=str(context.bot_app_id),
                telegram_user_id=context.provider_user_id,
                telegram_chat_id=context.provider_chat_id,
                contact_user_id=update.contact_user_id,
                contact_phone=update.contact_phone_number,
                first_name=update.provider_first_name,
                last_name=update.provider_last_name,
                language_code=update.provider_language_code,
                request_id=context.request_id,
            )
        except IdentityDomainError:
            key = "enrollment.invalid_contact"
        else:
            key = "enrollment.complete"
        await self.bot.send_message(
            context.provider_chat_id,
            self.localizer.text(key, locale=locale),
        )
