"""Small typed container for long-lived infrastructure resources."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import FastAPI

from app.bootstrap.bot_apps import BotPlatform, create_bot_platform
from app.bootstrap.i18n import create_localization_runtime
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar
from app.core.config.settings import Settings
from app.core.db.database import Database
from app.core.i18n.localizer import LocalizationRuntime
from app.core.observability.telemetry import Telemetry
from app.infrastructure.bots.factory import BotProviderFactory
from app.infrastructure.bots.telegram.verifier import TelegramWebAppVerifier
from app.modules.booking.bootstrap import (
    BookingModuleRuntime,
    create_booking_runtime,
)
from app.modules.booking.bootstrap import (
    register_bot_apps as register_booking_bot_apps,
)
from app.modules.finance.bootstrap import FinanceModuleRuntime, create_finance_runtime
from app.modules.identity.bootstrap import (
    IdentityModuleRuntime,
    create_identity_runtime,
)
from app.modules.identity.bootstrap import (
    register_bot_apps as register_identity_bot_apps,
)
from app.modules.identity.infrastructure.settings import IdentityModuleSettings
from app.modules.identity.public import IdentityAccess
from app.modules.registry import ModuleBotBootstrap


@dataclass(slots=True)
class AppContainer:
    """Resources explicitly constructed once per FastAPI application instance."""

    settings: Settings
    database: Database
    telemetry: Telemetry
    localization: LocalizationRuntime
    bot_platform: BotPlatform
    booking: BookingModuleRuntime
    identity: IdentityModuleRuntime
    identity_access: IdentityAccess
    finance: FinanceModuleRuntime
    identity_bot_app_id: BotAppId


def create_container(
    settings: Settings,
    *,
    module_bot_bootstraps: Sequence[ModuleBotBootstrap] | None = None,
    bot_provider_factory: BotProviderFactory | None = None,
) -> AppContainer:
    """Construct resources without connecting to external dependencies."""

    telemetry = Telemetry(settings)
    localization = create_localization_runtime(settings, telemetry)
    database = Database(settings.database)
    identity_settings = IdentityModuleSettings()
    identity_bot_app_id = BotAppId(identity_settings.bot_app_id)
    identity_bot_settings = settings.bots.apps.get(identity_bot_app_id)
    identity_verifiers = (
        {str(identity_bot_app_id): TelegramWebAppVerifier(identity_bot_settings)}
        if identity_bot_settings is not None
        and identity_bot_settings.enabled
        and identity_bot_settings.token is not None
        else {}
    )
    identity = create_identity_runtime(
        database=database,
        signing_secret=settings.security.resolved_session_signing_secret,
        web_app_verifiers=identity_verifiers,
        settings=identity_settings,
    )
    finance = create_finance_runtime(database=database)
    booking_bot_settings = settings.bots.apps.get(BotAppId("booking_bot"))
    web_app_verifiers = (
        {"booking_bot": TelegramWebAppVerifier(booking_bot_settings)}
        if booking_bot_settings is not None
        and booking_bot_settings.enabled
        and booking_bot_settings.token is not None
        else {}
    )
    booking = create_booking_runtime(
        database=database,
        session_signing_secret=settings.security.resolved_session_signing_secret,
        session_token_ttl_seconds=settings.security.session_token_ttl_seconds,
        web_app_verifiers=web_app_verifiers,
    )
    effective_bot_bootstraps: Sequence[ModuleBotBootstrap] = module_bot_bootstraps or ()
    default_bootstraps: list[ModuleBotBootstrap] = []
    if module_bot_bootstraps is None and identity_bot_settings is not None:

        def register_identity(registrar: BotAppRegistrar) -> None:
            """Bind the shared Identity runtime to its configured bot app."""

            register_identity_bot_apps(registrar, runtime=identity)

        default_bootstraps.append(register_identity)

    if module_bot_bootstraps is None and booking_bot_settings is not None:

        def register_booking(registrar: BotAppRegistrar) -> None:
            """Bind the constructed booking module runtime to its one configured bot app."""

            register_booking_bot_apps(registrar, runtime=booking)

        default_bootstraps.append(register_booking)
    if module_bot_bootstraps is None:
        effective_bot_bootstraps = tuple(default_bootstraps)
    return AppContainer(
        settings=settings,
        database=database,
        telemetry=telemetry,
        localization=localization,
        bot_platform=create_bot_platform(
            settings=settings,
            localization=localization,
            module_bootstraps=effective_bot_bootstraps,
            provider_factory=bot_provider_factory,
            telemetry=telemetry,
        ),
        booking=booking,
        identity=identity,
        identity_access=identity.service,
        finance=finance,
        identity_bot_app_id=identity_bot_app_id,
    )


def get_container_from_app(app: FastAPI) -> AppContainer:
    """Read the typed container from application state at the delivery boundary."""

    container = getattr(app.state, "container", None)
    if not isinstance(container, AppContainer):
        raise RuntimeError("Application container has not been configured.")
    return container
