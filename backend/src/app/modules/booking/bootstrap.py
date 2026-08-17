"""Booking runtime assembly called only from the global composition root."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.core.bots.contracts import TelegramWebAppInitDataVerifier
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar, BotHandlerDependencies
from app.core.db.database import Database
from app.modules.booking.application.access import (
    BookingAccessService,
    BookingPlatformAccessService,
    RbacSynchronizer,
)
from app.modules.booking.application.access_management import BookingAccessManagementService
from app.modules.booking.application.analytics import BookingAnalyticsService
from app.modules.booking.application.auth import BookingAuthService
from app.modules.booking.application.management import BookingManagementService
from app.modules.booking.application.service import BookingService
from app.modules.booking.application.telegram import BookingTelegramService
from app.modules.booking.infrastructure.auth.session import BookingSessionCodec
from app.modules.booking.infrastructure.settings import BookingModuleSettings
from app.modules.booking.presentation.telegram.handler import BookingTelegramHandler


@dataclass(frozen=True, slots=True)
class BookingModuleRuntime:
    """Module-owned services exposed to thin HTTP and bot adapters."""

    service: BookingService
    management: BookingManagementService
    analytics: BookingAnalyticsService
    access: BookingAccessService
    platform_access: BookingPlatformAccessService
    access_management: BookingAccessManagementService
    rbac_synchronizer: RbacSynchronizer
    auth: BookingAuthService
    telegram: BookingTelegramService
    database: Database
    settings: BookingModuleSettings


def create_booking_runtime(
    *,
    database: Database,
    session_signing_secret: str,
    session_token_ttl_seconds: int,
    web_app_verifiers: Mapping[str, TelegramWebAppInitDataVerifier],
    settings: BookingModuleSettings | None = None,
) -> BookingModuleRuntime:
    """Construct booking services from explicit, scoped technical capabilities."""

    module_settings = settings or BookingModuleSettings()
    session_codec = BookingSessionCodec(
        signing_secret=session_signing_secret,
        token_ttl_seconds=session_token_ttl_seconds,
    )
    access = BookingAccessService(database=database)
    service = BookingService(
        database=database,
        availability_max_days=module_settings.availability_max_days,
    )
    management = BookingManagementService(database=database)
    return BookingModuleRuntime(
        service=service,
        management=management,
        analytics=BookingAnalyticsService(database=database),
        auth=BookingAuthService(
            database=database,
            access=access,
            session_codec=session_codec,
            web_app_verifiers=web_app_verifiers,
            max_init_data_age_seconds=module_settings.webapp_max_age_seconds,
            auth_rate_limit_requests=module_settings.auth_rate_limit_requests,
            auth_rate_limit_window_seconds=module_settings.auth_rate_limit_window_seconds,
        ),
        access=access,
        platform_access=BookingPlatformAccessService(database=database),
        access_management=BookingAccessManagementService(database=database),
        rbac_synchronizer=RbacSynchronizer(database=database),
        telegram=BookingTelegramService(
            database=database,
            access=access,
            booking=service,
            management=management,
            callback_ttl_seconds=module_settings.callback_ttl_seconds,
        ),
        database=database,
        settings=module_settings,
    )


def register_bot_apps(registrar: BotAppRegistrar, *, runtime: BookingModuleRuntime) -> None:
    """Declare booking_bot ownership with only an app-bound gateway/localizer for handlers."""

    def create_handler(dependencies: BotHandlerDependencies) -> BookingTelegramHandler:
        """Bind the module's preconstructed application service to one isolated bot app runtime."""

        return BookingTelegramHandler(
            bot=dependencies.bot,
            localizer=dependencies.localizer,
            service=runtime.telegram,
        )

    registrar.register(
        owner_module="booking",
        app_id=BotAppId("booking_bot"),
        translation_domain="booking",
        module_root=Path(__file__).resolve().parent,
        handler_factory=create_handler,
    )
