"""Thin Telegram contact-enrollment handler."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.bots.context import BotUpdateContext
from app.core.bots.contracts import BotReplyButton, BotUpdate, ScopedBotGateway
from app.core.i18n.contracts import ScopedLocalizer
from app.core.i18n.locale import Locale
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.errors import IdentityDomainError
from app.modules.identity.domain.start_payload import parse_phone_challenge_start_parameter


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
        challenge_id = parse_phone_challenge_start_parameter(update.message_text)
        if challenge_id is not None:
            try:
                delivery = await self.service.claim_phone_challenge(
                    challenge_id=challenge_id,
                    bot_app_id=str(context.bot_app_id),
                    telegram_user_id=context.provider_user_id,
                    telegram_chat_id=context.provider_chat_id,
                    request_id=context.request_id,
                )
            except IdentityDomainError:
                await self.bot.send_message(
                    context.provider_chat_id,
                    self.localizer.text("authentication.link_invalid", locale=locale),
                )
                return
            if delivery is not None:
                await self._send_code(
                    recipient_id=context.provider_chat_id,
                    locale=locale,
                    code=delivery.code,
                )
                return
            await self._request_contact(context.provider_chat_id, locale=locale)
            return
        if update.message_text is not None and update.message_text.strip().startswith(
            "/start login_"
        ):
            await self.bot.send_message(
                context.provider_chat_id,
                self.localizer.text("authentication.link_invalid", locale=locale),
            )
            return
        if update.contact_phone_number is None:
            await self._request_contact(context.provider_chat_id, locale=locale)
            return
        try:
            result = await self.service.enroll_telegram_contact(
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
            if result.delivery is not None:
                await self._send_code(
                    recipient_id=context.provider_chat_id,
                    locale=locale,
                    code=result.delivery.code,
                )
                return
            key = "enrollment.complete"
        await self.bot.send_message(
            context.provider_chat_id,
            self.localizer.text(key, locale=locale),
        )

    async def _request_contact(self, recipient_id: str, *, locale: Locale) -> None:
        await self.bot.send_message(
            recipient_id,
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

    async def _send_code(self, *, recipient_id: str, locale: Locale, code: str) -> None:
        await self.bot.send_message(
            recipient_id,
            self.localizer.text(
                "authentication.code",
                locale=locale,
                params={"code": code},
            ),
        )
