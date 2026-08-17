"""Immutable context passed from a bot runtime to one module handler."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.bots.enums import BotProvider
from app.core.bots.ids import BotAppId
from app.core.i18n.locale import Locale


@dataclass(frozen=True, slots=True)
class BotUpdateContext:
    """Provider-neutral, app-bound metadata for one inbound update."""

    bot_app_id: BotAppId
    owner_module: str
    locale: Locale
    provider: BotProvider
    provider_update_id: str | None
    provider_user_id: str | None
    provider_chat_id: str | None
    request_id: str
