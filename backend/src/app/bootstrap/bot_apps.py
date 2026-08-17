"""Composition-root assembly for isolated bot registrations and runtimes."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from enum import StrEnum

from app.core.bots.contracts import BotMessageResult, BotProviderAdapter
from app.core.bots.enums import BotProvider
from app.core.bots.errors import (
    BotMalformedUpdateError,
    BotProviderFailureError,
    BotRegistrationError,
    BotRuntimeError,
    BotUpdateTimeoutError,
)
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar, BotAppRegistration, BotHandlerDependencies
from app.core.config.settings import Settings
from app.core.i18n.localizer import LocalizationRuntime, ModuleCatalogRegistration
from app.core.observability.telemetry import Telemetry
from app.infrastructure.bots.factory import BotProviderFactory, DefaultBotProviderFactory
from app.infrastructure.bots.registry import BotRuntimeRegistry
from app.infrastructure.bots.runtime import BotRuntime, RuntimeScopedBotGateway
from app.infrastructure.bots.telegram.verifier import verify_telegram_webhook_secret
from app.modules.registry import ModuleBotBootstrap, registered_bot_bootstraps


class WebhookDispatchResult(StrEnum):
    """Non-revealing outcomes mapped by the HTTP webhook adapter."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    MALFORMED = "malformed"
    TIMED_OUT = "timed_out"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class BotPlatform:
    """Own all runtime construction while keeping registries private to bootstrap."""

    def __init__(
        self,
        *,
        settings: Settings,
        localization: LocalizationRuntime,
        registrations: tuple[BotAppRegistration, ...],
        provider_factory: BotProviderFactory,
        telemetry: Telemetry,
    ) -> None:
        self._settings = settings
        self._localization = localization
        self._registrations = registrations
        self._provider_factory = provider_factory
        self._telemetry = telemetry
        self._registry: BotRuntimeRegistry | None = None
        self._initialized = False

    @property
    def is_ready(self) -> bool:
        """Return local startup validity without contacting external bot providers."""

        return (
            self._initialized and self._registry is not None and self._localization.is_initialized
        )

    async def initialize(self) -> None:
        """Validate ownership, load catalogs, and build one runtime per enabled bot."""

        if self._initialized:
            return
        self._validate_ownership()
        self._localization.initialize(self._catalog_registrations())
        adapters: list[BotProviderAdapter] = []
        runtimes: list[BotRuntime] = []
        try:
            registrations_by_id = {
                registration.app_id: registration for registration in self._registrations
            }
            for app_id, app_settings in self._settings.bots.apps.items():
                if not app_settings.enabled:
                    continue
                registration = registrations_by_id[app_id]
                adapter = self._provider_factory.create(app_id, app_settings)
                adapters.append(adapter)
                localizer = self._localization.scoped_localizer(
                    module_name=registration.owner_module,
                    translation_domain=registration.translation_domain,
                    bot_app_id=app_id,
                    bot_default_locale=app_settings.default_locale,
                )
                handler = registration.handler_factory(
                    BotHandlerDependencies(
                        bot=RuntimeScopedBotGateway(adapter, self._telemetry),
                        localizer=localizer,
                    )
                )
                runtimes.append(
                    BotRuntime(
                        registration=registration,
                        settings=app_settings,
                        adapter=adapter,
                        handler=handler,
                        global_default_locale=self._settings.i18n.default_locale,
                        telemetry=self._telemetry,
                    )
                )
            registry = BotRuntimeRegistry(runtimes)
            for runtime in runtimes:
                await runtime.validate_identity()
        except Exception:
            await asyncio.gather(*(adapter.close() for adapter in adapters), return_exceptions=True)
            self._localization.shutdown()
            raise
        self._registry = registry
        self._initialized = True

    async def shutdown(self) -> None:
        """Close every runtime before dropping catalog state for this app instance."""

        registry = self._registry
        self._registry = None
        self._initialized = False
        try:
            if registry is not None:
                await registry.close()
        finally:
            self._localization.shutdown()

    async def dispatch_telegram(
        self,
        app_id: BotAppId,
        *,
        presented_secret: str | None,
        payload: bytes,
        request_id: str,
    ) -> WebhookDispatchResult:
        """Verify the exact app secret before routing its payload to one handler."""

        registry = self._registry
        if registry is None:
            return WebhookDispatchResult.UNAVAILABLE
        runtime = registry.get(app_id)
        if (
            runtime is None
            or runtime.provider is not BotProvider.TELEGRAM
            or not runtime.webhook_enabled
        ):
            return WebhookDispatchResult.NOT_FOUND
        if not verify_telegram_webhook_secret(runtime.webhook_secret, presented_secret):
            return WebhookDispatchResult.REJECTED
        try:
            await runtime.dispatch(payload, request_id=request_id)
        except BotMalformedUpdateError:
            return WebhookDispatchResult.MALFORMED
        except BotUpdateTimeoutError:
            return WebhookDispatchResult.TIMED_OUT
        except (BotProviderFailureError, BotRuntimeError):
            return WebhookDispatchResult.FAILED
        return WebhookDispatchResult.ACCEPTED

    async def send_message(
        self,
        app_id: BotAppId,
        *,
        recipient_id: str,
        text: str,
    ) -> BotMessageResult:
        """Send an app-bound outbound message without exposing the private runtime registry."""

        registry = self._registry
        if registry is None:
            raise BotRuntimeError("Bot platform is not initialized.")
        runtime = registry.get(app_id)
        if runtime is None:
            raise BotRuntimeError(f"Bot app '{app_id}' is unavailable.")
        gateway = RuntimeScopedBotGateway(runtime.adapter, self._telemetry)
        return await gateway.send_message(recipient_id, text)

    def _validate_ownership(self) -> None:
        """Reject unknown registrations and enabled apps without exactly one owner."""

        registered_ids = {registration.app_id for registration in self._registrations}
        configured_ids = set(self._settings.bots.apps)
        unknown_registrations = registered_ids - configured_ids
        if unknown_registrations:
            rendered = ", ".join(sorted(map(str, unknown_registrations)))
            raise BotRegistrationError(f"Registered bot apps are not configured: {rendered}.")
        enabled_ids = {
            app_id
            for app_id, app_settings in self._settings.bots.apps.items()
            if app_settings.enabled
        }
        unregistered_enabled = enabled_ids - registered_ids
        if unregistered_enabled:
            rendered = ", ".join(sorted(map(str, unregistered_enabled)))
            raise BotRegistrationError(f"Enabled bot apps are unregistered: {rendered}.")

    def _catalog_registrations(self) -> tuple[ModuleCatalogRegistration, ...]:
        """Create catalog registrations only for explicitly registered module-owned apps."""

        return tuple(
            ModuleCatalogRegistration(
                module_name=registration.owner_module,
                bot_app_id=registration.app_id,
                translation_domain=registration.translation_domain,
                module_root=registration.module_root,
                supported_locales=self._settings.bots.apps[registration.app_id].supported_locales,
            )
            for registration in self._registrations
        )


def create_bot_platform(
    *,
    settings: Settings,
    localization: LocalizationRuntime,
    module_bootstraps: Sequence[ModuleBotBootstrap] | None = None,
    provider_factory: BotProviderFactory | None = None,
    telemetry: Telemetry,
) -> BotPlatform:
    """Collect module declarations while withholding settings and runtime registry access."""

    registrar = BotAppRegistrar()
    for bootstrap in module_bootstraps or registered_bot_bootstraps():
        bootstrap(registrar)
    return BotPlatform(
        settings=settings,
        localization=localization,
        registrations=registrar.freeze(),
        provider_factory=provider_factory or DefaultBotProviderFactory(),
        telemetry=telemetry,
    )
