"""Identity runtime assembly at the global composition root."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.core.bots.contracts import TelegramWebAppInitDataVerifier
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar, BotHandlerDependencies
from app.core.db.database import Database
from app.modules.identity.application.service import IdentityService
from app.modules.identity.infrastructure.settings import IdentityModuleSettings
from app.modules.identity.presentation.telegram.handler import IdentityTelegramHandler


@dataclass(frozen=True, slots=True)
class IdentityModuleRuntime:
    """Identity capabilities exposed to HTTP and bot presentation adapters."""

    service: IdentityService
    settings: IdentityModuleSettings


def create_identity_runtime(
    *,
    database: Database,
    signing_secret: str,
    web_app_verifiers: Mapping[str, TelegramWebAppInitDataVerifier],
    settings: IdentityModuleSettings | None = None,
) -> IdentityModuleRuntime:
    module_settings = settings or IdentityModuleSettings()
    return IdentityModuleRuntime(
        service=IdentityService(
            database=database,
            signing_secret=signing_secret,
            otp_ttl_seconds=module_settings.otp_ttl_seconds,
            otp_attempts=module_settings.otp_attempts,
            access_token_ttl_seconds=module_settings.access_token_ttl_seconds,
            web_app_verifiers=web_app_verifiers,
            webapp_max_age_seconds=module_settings.webapp_max_age_seconds,
        ),
        settings=module_settings,
    )


def register_bot_apps(registrar: BotAppRegistrar, *, runtime: IdentityModuleRuntime) -> None:
    """Declare the one isolated Spacewhy auth bot owned by Identity."""

    def create_handler(dependencies: BotHandlerDependencies) -> IdentityTelegramHandler:
        return IdentityTelegramHandler(
            bot=dependencies.bot,
            localizer=dependencies.localizer,
            service=runtime.service,
        )

    registrar.register(
        owner_module="identity",
        app_id=BotAppId(runtime.settings.bot_app_id),
        translation_domain="identity",
        module_root=Path(__file__).resolve().parent,
        handler_factory=create_handler,
    )
