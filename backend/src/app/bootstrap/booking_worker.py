"""Composition-root adapters for the booking background worker."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.bootstrap.bot_apps import BotPlatform
from app.bootstrap.container import AppContainer
from app.core.bots.errors import BotRuntimeError
from app.core.bots.ids import BotAppId
from app.core.config.settings import Settings
from app.core.i18n.errors import InterpolationError, MissingTranslationError
from app.core.i18n.locale import Locale
from app.core.i18n.localizer import LocalizationRuntime
from app.infrastructure.bots.telegram.errors import TelegramRecipientUnavailableError
from app.modules.booking.infrastructure.jobs.worker import (
    BookingOutboxWorker,
    PermanentNotificationDeliveryError,
)


@dataclass(frozen=True, slots=True)
class BookingTelegramOutboxDelivery:
    """Render module-owned i18n content and send it through exactly one configured bot app."""

    settings: Settings
    localization: LocalizationRuntime
    bot_platform: BotPlatform

    async def deliver(
        self,
        *,
        bot_app_id: str,
        chat_id: str,
        locale: str,
        template_key: str,
        params: Mapping[str, object],
    ) -> None:
        """Use only an app-bound localizer and gateway; never inspect a token or registry."""

        try:
            app_id = BotAppId(bot_app_id)
            app_settings = self.settings.bots.apps.get(app_id)
            if app_settings is None or not app_settings.enabled:
                raise PermanentNotificationDeliveryError("Configured bot app is unavailable.")
            requested_locale = Locale.parse(locale)
            if requested_locale not in app_settings.supported_locales:
                requested_locale = app_settings.default_locale
            localizer = self.localization.scoped_localizer(
                module_name="booking",
                translation_domain="booking",
                bot_app_id=app_id,
                bot_default_locale=app_settings.default_locale,
            )
            text = localizer.text(template_key, locale=requested_locale, params=params)
        except (InterpolationError, MissingTranslationError, ValueError) as error:
            raise PermanentNotificationDeliveryError("Notification rendering failed.") from error
        try:
            await self.bot_platform.send_message(
                app_id,
                recipient_id=chat_id,
                text=text,
            )
        except TelegramRecipientUnavailableError as error:
            raise PermanentNotificationDeliveryError("Recipient is unavailable.") from error
        except BotRuntimeError as error:
            raise PermanentNotificationDeliveryError(
                "Configured bot app is unavailable."
            ) from error


def create_booking_worker(container: AppContainer) -> BookingOutboxWorker:
    """Build the worker only after the container owns initialized database and bot resources."""

    return BookingOutboxWorker(
        database=container.database,
        access=container.booking.access,
        delivery=BookingTelegramOutboxDelivery(
            settings=container.settings,
            localization=container.localization,
            bot_platform=container.bot_platform,
        ),
        poll_seconds=container.booking.settings.worker_poll_seconds,
        batch_size=container.booking.settings.worker_batch_size,
        lease_seconds=container.booking.settings.worker_lease_seconds,
        metrics=container.telemetry,
    )
