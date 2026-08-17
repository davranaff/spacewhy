"""Explicit composition-root index for future module bootstraps."""

from __future__ import annotations

from collections.abc import Callable

from app.core.bots.registration import BotAppRegistrar

ModuleBotBootstrap = Callable[[BotAppRegistrar], None]


def registered_bot_bootstraps() -> tuple[ModuleBotBootstrap, ...]:
    """Return known module registration functions without dynamic package discovery.

    The foundation has no business module yet. A future module adds only its own bootstrap
    function to this explicit composition-root index; it never reaches another module's internals.
    """

    return ()
