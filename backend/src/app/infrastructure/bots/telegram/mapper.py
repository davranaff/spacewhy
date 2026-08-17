"""Map aiogram update types into the small provider-neutral core input."""

from __future__ import annotations

from aiogram.types import Update

from app.core.bots.contracts import BotUpdate


def map_telegram_update(update: Update) -> BotUpdate:
    """Extract only stable metadata needed before a module defines bot commands."""

    if update.message is not None:
        message = update.message
        contact = message.contact
        return BotUpdate(
            provider_update_id=str(update.update_id),
            provider_user_id=str(message.from_user.id) if message.from_user is not None else None,
            provider_chat_id=str(message.chat.id),
            provider_language_code=(
                message.from_user.language_code if message.from_user is not None else None
            ),
            event_type="message",
            message_text=message.text,
            contact_user_id=(
                str(contact.user_id)
                if contact is not None and contact.user_id is not None
                else None
            ),
            contact_phone_number=contact.phone_number if contact is not None else None,
            provider_first_name=message.from_user.first_name
            if message.from_user is not None
            else None,
            provider_last_name=message.from_user.last_name
            if message.from_user is not None
            else None,
            provider_username=message.from_user.username if message.from_user is not None else None,
        )
    if update.edited_message is not None:
        message = update.edited_message
        return BotUpdate(
            provider_update_id=str(update.update_id),
            provider_user_id=str(message.from_user.id) if message.from_user is not None else None,
            provider_chat_id=str(message.chat.id),
            provider_language_code=(
                message.from_user.language_code if message.from_user is not None else None
            ),
            event_type="edited_message",
            message_text=message.text,
            provider_first_name=message.from_user.first_name
            if message.from_user is not None
            else None,
            provider_last_name=message.from_user.last_name
            if message.from_user is not None
            else None,
            provider_username=message.from_user.username if message.from_user is not None else None,
        )
    if update.callback_query is not None:
        callback = update.callback_query
        chat = callback.message.chat if callback.message is not None else None
        return BotUpdate(
            provider_update_id=str(update.update_id),
            provider_user_id=str(callback.from_user.id),
            provider_chat_id=str(chat.id) if chat is not None else None,
            provider_language_code=callback.from_user.language_code,
            event_type="callback_query",
            callback_data=callback.data,
            callback_id=callback.id,
            provider_first_name=callback.from_user.first_name,
            provider_last_name=callback.from_user.last_name,
            provider_username=callback.from_user.username,
        )
    return BotUpdate(
        provider_update_id=str(update.update_id),
        provider_user_id=None,
        provider_chat_id=None,
        provider_language_code=None,
        event_type="unsupported",
    )
