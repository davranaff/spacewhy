"""Per-app bot runtime that never broadcasts updates or shares mutable context."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter

from pydantic import SecretStr

from app.core.bots.context import BotUpdateContext
from app.core.bots.contracts import (
    BotInlineButton,
    BotMessageResult,
    BotProviderAdapter,
    BotReplyButton,
    BotUpdateHandler,
)
from app.core.bots.enums import BotProvider
from app.core.bots.errors import (
    BotMalformedUpdateError,
    BotProviderFailureError,
    BotRuntimeError,
    BotUpdateTimeoutError,
)
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistration
from app.core.bots.settings import BotAppSettings
from app.core.i18n.locale import Locale
from app.core.i18n.resolver import resolve_bot_locale
from app.core.observability.telemetry import Telemetry

logger = logging.getLogger("spacewhy")


@dataclass(frozen=True, slots=True)
class RuntimeScopedBotGateway:
    """Expose only outbound behavior for one adapter to its owning module handler."""

    _adapter: BotProviderAdapter
    _telemetry: Telemetry

    @property
    def app_id(self) -> BotAppId:
        """Return the app ID permanently bound to this gateway."""

        return self._adapter.app_id

    @property
    def provider(self) -> BotProvider:
        """Return the provider permanently bound to this gateway."""

        return self._adapter.provider

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        *,
        inline_keyboard: tuple[tuple[BotInlineButton, ...], ...] | None = None,
        reply_keyboard: tuple[tuple[BotReplyButton, ...], ...] | None = None,
    ) -> BotMessageResult:
        """Delegate outbound traffic and record only a low-cardinality outcome."""

        try:
            result = await self._adapter.send_message(
                recipient_id,
                text,
                inline_keyboard=inline_keyboard,
                reply_keyboard=reply_keyboard,
            )
        except Exception:
            self._telemetry.record_bot_outbound_message(
                bot_app_id=str(self.app_id),
                provider=self.provider.value,
                result="failed",
            )
            raise
        self._telemetry.record_bot_outbound_message(
            bot_app_id=str(self.app_id),
            provider=self.provider.value,
            result="success",
        )
        return result

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Acknowledge a callback through the same isolated adapter without logging its payload."""

        await self._adapter.answer_callback(callback_id, text)


@dataclass(slots=True)
class BotRuntime:
    """One app-bound provider adapter, handler, settings boundary, and locale policy."""

    registration: BotAppRegistration
    settings: BotAppSettings
    adapter: BotProviderAdapter
    handler: BotUpdateHandler
    global_default_locale: Locale
    telemetry: Telemetry
    _closed: bool = False

    @property
    def app_id(self) -> BotAppId:
        """Return the public app identifier selected by this runtime."""

        return self.registration.app_id

    @property
    def provider(self) -> BotProvider:
        """Return the one provider bound to this runtime."""

        return self.settings.provider

    @property
    def webhook_secret(self) -> SecretStr | None:
        """Expose a masked secret only to the bootstrap webhook verifier."""

        return self.settings.webhook_secret

    @property
    def webhook_enabled(self) -> bool:
        """Return whether this runtime accepts provider webhook updates."""

        return self.settings.webhook_enabled

    async def dispatch(
        self,
        payload: bytes,
        *,
        request_id: str,
        stored_user_locale: Locale | None = None,
        conversation_locale: Locale | None = None,
    ) -> None:
        """Parse and send one update to this exact app's handler only."""

        started_at = perf_counter()
        try:
            with self.telemetry.start_bot_update_span(
                bot_app_id=str(self.app_id),
                owner_module=self.registration.owner_module,
                provider=self.provider.value,
                request_id=request_id,
            ):
                async with asyncio.timeout(self.settings.processing_timeout_seconds):
                    update = await self.adapter.parse_update(payload)
                    locale = resolve_bot_locale(
                        supported_locales=self.settings.supported_locales,
                        bot_default_locale=self.settings.default_locale,
                        global_default_locale=self.global_default_locale,
                        stored_user_locale=stored_user_locale,
                        conversation_locale=conversation_locale,
                        provider_language_code=update.provider_language_code,
                    )
                    context = BotUpdateContext(
                        bot_app_id=self.app_id,
                        owner_module=self.registration.owner_module,
                        locale=locale,
                        provider=self.provider,
                        provider_update_id=update.provider_update_id,
                        provider_user_id=update.provider_user_id,
                        provider_chat_id=update.provider_chat_id,
                        request_id=request_id,
                    )
                    await self.handler.handle(context, update)
            self._record_update(result="success", started_at=started_at)
        except TimeoutError as error:
            self._record_update(result="timeout", started_at=started_at)
            logger.warning(
                "bot_update_timed_out",
                extra={
                    "request_id": request_id,
                    "bot_app_id": self.app_id,
                    "owner_module": self.registration.owner_module,
                    "provider": self.provider,
                    "result": "timeout",
                },
            )
            raise BotUpdateTimeoutError(
                f"Bot app '{self.app_id}' update processing timed out."
            ) from error
        except (BotMalformedUpdateError, BotRuntimeError):
            self._record_update(result="rejected", started_at=started_at)
            raise
        except Exception as error:
            self._record_update(result="failed", started_at=started_at)
            logger.warning(
                "bot_update_failed",
                extra={
                    "request_id": request_id,
                    "bot_app_id": self.app_id,
                    "owner_module": self.registration.owner_module,
                    "provider": self.provider,
                    "result": "failed",
                },
            )
            raise BotProviderFailureError(
                f"Bot app '{self.app_id}' update could not be processed."
            ) from error

    async def validate_identity(self) -> None:
        """Verify optional expected identity for this client without logging credentials."""

        if not self.settings.validate_identity_on_startup:
            return
        try:
            identity = await self.adapter.validate_identity()
        except Exception as error:
            raise BotProviderFailureError(
                f"Bot app '{self.app_id}' identity validation failed."
            ) from error
        if (
            self.settings.expected_bot_id is not None
            and identity.provider_bot_id != self.settings.expected_bot_id
        ):
            raise BotRuntimeError(f"Bot app '{self.app_id}' identity validation failed.")
        if (
            self.settings.expected_username is not None
            and identity.username != self.settings.expected_username
        ):
            raise BotRuntimeError(f"Bot app '{self.app_id}' identity validation failed.")

    async def close(self) -> None:
        """Close this exact provider adapter once."""

        if self._closed:
            return
        self._closed = True
        await self.adapter.close()

    def _record_update(self, *, result: str, started_at: float) -> None:
        """Emit low-cardinality runtime metrics without update/user identifiers."""

        self.telemetry.record_bot_update(
            bot_app_id=str(self.app_id),
            provider=self.provider.value,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
