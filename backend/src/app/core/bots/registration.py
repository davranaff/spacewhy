"""Explicit module ownership declarations for isolated bot applications."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.bots.contracts import BotUpdateHandler, ScopedBotGateway
from app.core.bots.errors import BotRegistrationError
from app.core.bots.ids import BotAppId
from app.core.i18n.contracts import ScopedLocalizer

_OWNERSHIP_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


@dataclass(frozen=True, slots=True)
class BotHandlerDependencies:
    """Only scoped capabilities made available to a module bot handler factory."""

    bot: ScopedBotGateway
    localizer: ScopedLocalizer


BotHandlerFactory = Callable[[BotHandlerDependencies], BotUpdateHandler]


@dataclass(frozen=True, slots=True)
class BotAppRegistration:
    """A module's declaration that it exclusively owns one configured bot app."""

    owner_module: str
    app_id: BotAppId
    translation_domain: str
    module_root: Path
    handler_factory: BotHandlerFactory


class BotAppRegistrar:
    """Collect one-time ownership declarations without exposing settings or runtimes."""

    def __init__(self) -> None:
        self._registrations: dict[BotAppId, BotAppRegistration] = {}
        self._frozen = False

    def register(
        self,
        *,
        owner_module: str,
        app_id: BotAppId,
        translation_domain: str,
        module_root: Path,
        handler_factory: BotHandlerFactory,
    ) -> None:
        """Declare an app's owner, catalog boundary, and deferred handler construction."""

        if self._frozen:
            raise BotRegistrationError("Bot app registration is immutable after startup.")
        if not _OWNERSHIP_NAME_PATTERN.fullmatch(owner_module):
            raise BotRegistrationError("Bot app owner module has an invalid name.")
        if not _OWNERSHIP_NAME_PATTERN.fullmatch(translation_domain):
            raise BotRegistrationError("Bot app translation domain has an invalid name.")
        if not callable(handler_factory):
            raise BotRegistrationError("Bot app handler factory must be callable.")
        if app_id in self._registrations:
            raise BotRegistrationError(f"Bot app '{app_id}' is registered more than once.")
        self._registrations[app_id] = BotAppRegistration(
            owner_module=owner_module,
            app_id=app_id,
            translation_domain=translation_domain,
            module_root=module_root,
            handler_factory=handler_factory,
        )

    def freeze(self) -> tuple[BotAppRegistration, ...]:
        """Prevent late ownership changes and return a deterministic registration snapshot."""

        self._frozen = True
        return tuple(self._registrations[app_id] for app_id in sorted(self._registrations))
