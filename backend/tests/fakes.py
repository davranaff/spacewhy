"""Provider-neutral bot fakes and temporary gettext catalogs for isolated tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from app.core.bots.context import BotUpdateContext
from app.core.bots.contracts import (
    BotInlineButton,
    BotMessageResult,
    BotProviderIdentity,
    BotReplyButton,
    BotUpdate,
    BotUpdateHandler,
)
from app.core.bots.enums import BotProvider
from app.core.bots.errors import BotMalformedUpdateError, BotProviderFailureError
from app.core.bots.ids import BotAppId
from app.core.bots.registration import BotAppRegistrar, BotHandlerDependencies
from app.core.bots.settings import BotAppSettings
from app.infrastructure.bots.factory import BotProviderFactory
from app.modules.registry import ModuleBotBootstrap


def _empty_sent_messages() -> list[tuple[str, str]]:
    """Return a typed mutable log for one fake adapter."""

    return []


def _empty_identities() -> dict[BotAppId, BotProviderIdentity]:
    """Return a typed per-app fake identity mapping."""

    return {}


def _empty_adapters() -> dict[BotAppId, FakeBotAdapter]:
    """Return a typed per-app fake client mapping."""

    return {}


def _empty_received_updates() -> list[tuple[BotUpdateContext, BotUpdate]]:
    """Return a typed update-recording list."""

    return []


@dataclass(slots=True)
class FakeBotAdapter:
    """One fake client per app that records only safe test metadata."""

    bound_app_id: BotAppId
    identity: BotProviderIdentity = field(
        default_factory=lambda: BotProviderIdentity(provider_bot_id=1, username="test_bot")
    )
    sent_messages: list[tuple[str, str]] = field(default_factory=_empty_sent_messages)
    close_calls: int = 0
    fail_identity: bool = False

    @property
    def app_id(self) -> BotAppId:
        """Return the one app this fake represents."""

        return self.bound_app_id

    @property
    def provider(self) -> BotProvider:
        """Match the first production provider without any network behavior."""

        return BotProvider.TELEGRAM

    async def send_message(
        self,
        recipient_id: str,
        text: str,
        *,
        inline_keyboard: tuple[tuple[BotInlineButton, ...], ...] | None = None,
        reply_keyboard: tuple[tuple[BotReplyButton, ...], ...] | None = None,
    ) -> BotMessageResult:
        """Record outbound traffic on this app only."""

        del inline_keyboard, reply_keyboard
        self.sent_messages.append((recipient_id, text))
        return BotMessageResult(provider_message_id=str(len(self.sent_messages)))

    async def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        """Accept a test callback acknowledgement without extending the safe message test log."""

        del callback_id, text

    async def parse_update(self, payload: bytes) -> BotUpdate:
        """Map a small test JSON payload into the provider-neutral update contract."""

        try:
            raw_value: object = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BotMalformedUpdateError("Fake bot payload is invalid.") from error
        if not isinstance(raw_value, Mapping):
            raise BotMalformedUpdateError("Fake bot payload is invalid.")
        raw = cast(Mapping[str, object], raw_value)
        return BotUpdate(
            provider_update_id=_optional_text(raw.get("update_id")),
            provider_user_id=_optional_text(raw.get("user_id")),
            provider_chat_id=_optional_text(raw.get("chat_id")),
            provider_language_code=_optional_text(raw.get("language_code")),
            event_type="message",
        )

    async def validate_identity(self) -> BotProviderIdentity:
        """Return an injected fake identity or a sanitized failure."""

        if self.fail_identity:
            raise BotProviderFailureError("Fake identity validation failed.")
        return self.identity

    async def close(self) -> None:
        """Track exactly-once shutdown behavior."""

        self.close_calls += 1


def _optional_text(value: object) -> str | None:
    """Coerce simple fixture values without accepting nested payload data."""

    return str(value) if isinstance(value, str | int) else None


@dataclass(slots=True)
class FakeBotProviderFactory(BotProviderFactory):
    """Create independently recordable fake adapters without looking at secret values."""

    identities: dict[BotAppId, BotProviderIdentity] = field(default_factory=_empty_identities)
    fail_for_app: BotAppId | None = None
    created: dict[BotAppId, FakeBotAdapter] = field(default_factory=_empty_adapters)

    def create(self, app_id: BotAppId, settings: BotAppSettings) -> FakeBotAdapter:
        """Build a test adapter that never accesses token or webhook settings."""

        del settings
        adapter = FakeBotAdapter(
            bound_app_id=app_id,
            identity=self.identities.get(
                app_id,
                BotProviderIdentity(provider_bot_id=1, username="test_bot"),
            ),
            fail_identity=app_id == self.fail_for_app,
        )
        self.created[app_id] = adapter
        return adapter


@dataclass(slots=True)
class RecordingHandler(BotUpdateHandler):
    """A generic test handler, not a product bot command implementation."""

    delay_seconds: float = 0.0
    received: list[tuple[BotUpdateContext, BotUpdate]] = field(
        default_factory=_empty_received_updates
    )

    async def handle(self, context: BotUpdateContext, update: BotUpdate) -> None:
        """Record the exact app-bound context after an optional deterministic delay."""

        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        self.received.append((context, update))


@dataclass(slots=True)
class RecordingHandlerFactory:
    """Capture only the scoped capabilities passed from composition root."""

    handler: RecordingHandler = field(default_factory=RecordingHandler)
    dependencies: BotHandlerDependencies | None = None

    def __call__(self, dependencies: BotHandlerDependencies) -> RecordingHandler:
        """Keep the dependency snapshot for isolation assertions."""

        self.dependencies = dependencies
        return self.handler


def bot_bootstrap(
    *,
    owner_module: str,
    app_id: BotAppId,
    module_root: Path,
    handler_factory: RecordingHandlerFactory,
    translation_domain: str | None = None,
) -> ModuleBotBootstrap:
    """Build a test-only module bootstrap with no product behavior."""

    def register(registrar: BotAppRegistrar) -> None:
        registrar.register(
            owner_module=owner_module,
            app_id=app_id,
            translation_domain=translation_domain or owner_module,
            module_root=module_root,
            handler_factory=handler_factory,
        )

    return register


def write_module_catalogs(
    *,
    module_root: Path,
    app_id: BotAppId,
    locales: tuple[str, ...] = ("en", "ru", "uz"),
    app_label: str | None = None,
) -> None:
    """Create test-only module common and bot override PO catalogs."""

    label = app_label or str(app_id)
    for locale in locales:
        _write_po(
            module_root / "locales" / "common" / locale / "messages.po",
            locale=locale,
            messages={
                "common.greeting": f"common-{locale}",
                "common.items": f"one-{locale}-{{count}}",
                "common.items_plural": f"many-{locale}-{{count}}",
            },
            plural_key="common.items",
        )
        _write_po(
            module_root / "locales" / "bots" / str(app_id) / locale / "messages.po",
            locale=locale,
            messages={
                "bot.greeting": f"{label}-{locale}",
            },
        )


def _write_po(
    path: Path,
    *,
    locale: str,
    messages: dict[str, str],
    plural_key: str | None = None,
) -> None:
    """Write one minimal valid gettext catalog for a temporary test module."""

    path.parent.mkdir(parents=True, exist_ok=True)
    plural_forms = (
        "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
        "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"
        if locale == "ru"
        else "nplurals=2; plural=(n != 1);"
    )
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: tests\\n"',
        f'"Language: {locale}\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        f'"Plural-Forms: {plural_forms}\\n"',
        "",
    ]
    for key, value in messages.items():
        if key == plural_key:
            plural_value = messages[f"{key}_plural"]
            lines.extend(
                [
                    f'msgid "{key}"',
                    f'msgid_plural "{key}_plural"',
                    f'msgstr[0] "{value}"',
                    f'msgstr[1] "{plural_value}"',
                ]
            )
            if locale == "ru":
                lines.append(f'msgstr[2] "{plural_value}"')
        elif not key.endswith("_plural"):
            lines.extend([f'msgid "{key}"', f'msgstr "{value}"'])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
