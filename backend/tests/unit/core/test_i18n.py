"""Babel/gettext catalog, locale resolution, and isolation unit coverage."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.core.bots.ids import BotAppId
from app.core.config.environment import Environment
from app.core.i18n.errors import CatalogValidationError, MissingTranslationError
from app.core.i18n.formatting import format_local_datetime
from app.core.i18n.locale import Locale
from app.core.i18n.localizer import LocalizationRuntime, ModuleCatalogRegistration
from app.core.i18n.resolver import (
    parse_accept_language,
    resolve_bot_locale,
    resolve_http_locale,
)
from app.core.i18n.settings import I18nSettings
from tests.fakes import write_module_catalogs


def _runtime() -> LocalizationRuntime:
    """Create a test runtime with the production-supported locale set."""

    return LocalizationRuntime(I18nSettings(), Environment.TEST)


def _module_registration(
    *,
    module_name: str,
    app_id: BotAppId,
    module_root: Path,
    translation_domain: str | None = None,
) -> ModuleCatalogRegistration:
    """Create a typed catalog registration for a temporary test module root."""

    return ModuleCatalogRegistration(
        module_name=module_name,
        bot_app_id=app_id,
        translation_domain=translation_domain or module_name,
        module_root=module_root,
        supported_locales=frozenset({Locale("en"), Locale("ru"), Locale("uz")}),
    )


def test_locale_normalization_and_supported_locale_resolution() -> None:
    """BCP 47 variants normalize to supported product tags and unsupported tags fall back."""

    assert Locale("ru-RU") == Locale("ru")
    assert Locale("en-US") == Locale("en")
    assert Locale("uz-UZ") == Locale("uz")
    assert Locale("uz-Latn-UZ") == Locale("uz-Latn")
    supported = frozenset({Locale("en"), Locale("ru"), Locale("uz")})
    assert resolve_http_locale(
        supported_locales=supported,
        default_locale=Locale("en"),
        accept_language="fr-FR, ru-RU;q=0.8",
    ) == Locale("ru")
    assert resolve_http_locale(
        supported_locales=supported,
        default_locale=Locale("en"),
        accept_language="fr-FR",
    ) == Locale("en")


def test_accept_language_parsing_is_bounded_and_deterministic() -> None:
    """Malformed ranges, wildcards, and overlong headers never become valid locales."""

    supported = frozenset({Locale("en"), Locale("ru"), Locale("uz")})
    assert parse_accept_language(
        "uz-UZ;q=0.7, ru-RU;q=0.9, en;q=0.4",
        supported_locales=supported,
        max_length=512,
    ) == Locale("ru")
    assert (
        parse_accept_language(
            "not a locale, *;q=1",
            supported_locales=supported,
            max_length=512,
        )
        is None
    )
    assert (
        parse_accept_language(
            "ru" * 400,
            supported_locales=supported,
            max_length=512,
        )
        is None
    )


def test_bot_locale_resolution_prefers_explicit_values_then_provider_then_defaults() -> None:
    """Bot updates never use a mutable process-wide current locale."""

    supported = frozenset({Locale("en"), Locale("ru"), Locale("uz")})
    assert resolve_bot_locale(
        supported_locales=supported,
        bot_default_locale=Locale("uz"),
        global_default_locale=Locale("en"),
        stored_user_locale=Locale("ru"),
        conversation_locale=Locale("uz"),
        provider_language_code="en-US",
    ) == Locale("ru")
    assert resolve_bot_locale(
        supported_locales=supported,
        bot_default_locale=Locale("uz"),
        global_default_locale=Locale("en"),
        provider_language_code="ru-RU",
    ) == Locale("ru")
    assert resolve_bot_locale(
        supported_locales=supported,
        bot_default_locale=Locale("uz"),
        global_default_locale=Locale("en"),
        provider_language_code="fr-FR",
    ) == Locale("uz")


def test_core_catalog_translates_ru_uz_and_en_with_pluralization() -> None:
    """The shipped platform catalog uses gettext rather than a global dictionary."""

    runtime = _runtime()
    runtime.initialize(())
    localizer = runtime.core_localizer()

    assert localizer.text("platform.temporary_unavailable", locale=Locale("en")) == (
        "Service temporarily unavailable."
    )
    assert localizer.text("platform.temporary_unavailable", locale=Locale("ru")) == (
        "Сервис временно недоступен."
    )
    assert localizer.text("platform.temporary_unavailable", locale=Locale("uz")) == (
        "Xizmat vaqtincha mavjud emas."
    )
    assert "2" in localizer.plural(
        "platform.retry_after_seconds",
        "platform.retry_after_seconds_plural",
        count=2,
        locale=Locale("en"),
    )


def test_scoped_localizer_uses_bot_override_then_module_common_without_crossing_scopes(
    tmp_path: Path,
) -> None:
    """A bot app and module can resolve only their own registered catalogs."""

    root = tmp_path
    support_app = BotAppId("support_bot")
    sales_app = BotAppId("sales_bot")
    write_module_catalogs(module_root=root, app_id=support_app, app_label="support")
    write_module_catalogs(module_root=root, app_id=sales_app, app_label="sales")
    runtime = _runtime()
    runtime.initialize(
        (
            _module_registration(
                module_name="support",
                app_id=support_app,
                module_root=root,
            ),
            _module_registration(
                module_name="support",
                app_id=sales_app,
                module_root=root,
            ),
        )
    )
    support = runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=support_app,
        bot_default_locale=Locale("en"),
    )
    sales = runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=sales_app,
        bot_default_locale=Locale("en"),
    )

    assert support.text("bot.greeting", locale=Locale("ru")) == "support-ru"
    assert sales.text("bot.greeting", locale=Locale("ru")) == "sales-ru"
    assert support.text("common.greeting", locale=Locale("uz")) == "common-uz"
    assert (
        support.plural(
            "common.items",
            "common.items_plural",
            count=2,
            locale=Locale("en"),
        )
        == "many-en-2"
    )


def test_localizer_does_not_fall_back_to_another_module_or_bot(
    tmp_path: Path,
) -> None:
    """Identical key names never cause an accidental cross-module translation lookup."""

    base = tmp_path
    support_root = base / "support"
    sales_root = base / "sales"
    support_app = BotAppId("support_bot")
    sales_app = BotAppId("sales_bot")
    write_module_catalogs(module_root=support_root, app_id=support_app, app_label="support")
    write_module_catalogs(module_root=sales_root, app_id=sales_app, app_label="sales")
    runtime = _runtime()
    runtime.initialize(
        (
            _module_registration(
                module_name="support",
                app_id=support_app,
                module_root=support_root,
            ),
            _module_registration(
                module_name="sales",
                app_id=sales_app,
                module_root=sales_root,
            ),
        )
    )
    support = runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=support_app,
        bot_default_locale=Locale("en"),
    )

    assert support.text("bot.greeting", locale=Locale("en")) == "support-en"
    with pytest.raises(MissingTranslationError):
        support.text("sales.only", locale=Locale("en"))


def test_catalog_validation_rejects_placeholder_mismatch_and_malformed_catalog(
    tmp_path: Path,
) -> None:
    """Startup validation catches bad source catalogs before traffic is accepted."""

    root = tmp_path
    app_id = BotAppId("support_bot")
    write_module_catalogs(module_root=root, app_id=app_id)
    ru_common = root / "locales" / "common" / "ru" / "messages.po"
    ru_common.write_text(
        ru_common.read_text(encoding="utf-8").replace("common-ru", "common-{name}"),
        encoding="utf-8",
    )
    runtime = _runtime()
    with pytest.raises(CatalogValidationError, match="placeholder"):
        runtime.initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=root,
                ),
            )
        )

    write_module_catalogs(module_root=root, app_id=app_id)
    malformed = root / "locales" / "bots" / str(app_id) / "en" / "messages.po"
    malformed.write_text("msgid broken", encoding="utf-8")
    with pytest.raises(CatalogValidationError):
        _runtime().initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=root,
                ),
            )
        )


def test_catalog_validation_rejects_duplicate_translation_keys(tmp_path: Path) -> None:
    """Duplicate PO keys are detected before gettext compilation can collapse them."""

    app_id = BotAppId("support_bot")
    write_module_catalogs(module_root=tmp_path, app_id=app_id)
    bot_catalog = tmp_path / "locales" / "bots" / str(app_id) / "en" / "messages.po"
    bot_catalog.write_text(
        bot_catalog.read_text(encoding="utf-8") + '\nmsgid "bot.greeting"\nmsgstr "duplicate"\n',
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="duplicate"):
        _runtime().initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=tmp_path,
                ),
            )
        )


def test_catalog_layout_rejects_unregistered_apps_unsupported_locales_and_domains(
    tmp_path: Path,
) -> None:
    """Unowned catalog paths cannot silently introduce a bot scope or locale."""

    app_id = BotAppId("support_bot")
    unregistered_root = tmp_path / "unregistered"
    write_module_catalogs(module_root=unregistered_root, app_id=app_id)
    (unregistered_root / "locales" / "bots" / "unknown_bot" / "en").mkdir(parents=True)
    with pytest.raises(CatalogValidationError, match="not registered"):
        _runtime().initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=unregistered_root,
                ),
            )
        )

    unsupported_locale_root = tmp_path / "unsupported-locale"
    write_module_catalogs(module_root=unsupported_locale_root, app_id=app_id)
    (unsupported_locale_root / "locales" / "common" / "fr").mkdir(parents=True)
    with pytest.raises(CatalogValidationError, match="unsupported locale"):
        _runtime().initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=unsupported_locale_root,
                ),
            )
        )

    conflict_root = tmp_path / "conflict"
    write_module_catalogs(module_root=conflict_root, app_id=app_id)
    second_app_id = BotAppId("operator_bot")
    write_module_catalogs(module_root=conflict_root, app_id=second_app_id)
    with pytest.raises(CatalogValidationError, match="conflicting translation domains"):
        _runtime().initialize(
            (
                _module_registration(
                    module_name="support",
                    app_id=app_id,
                    module_root=conflict_root,
                ),
                _module_registration(
                    module_name="support",
                    app_id=second_app_id,
                    module_root=conflict_root,
                    translation_domain="operator",
                ),
            )
        )


@pytest.mark.asyncio
async def test_concurrent_localizer_calls_keep_locale_values_isolated(
    tmp_path: Path,
) -> None:
    """Two concurrent calls never overwrite each other's resolved locale."""

    root = tmp_path
    app_id = BotAppId("support_bot")
    write_module_catalogs(module_root=root, app_id=app_id)
    runtime = _runtime()
    runtime.initialize(
        (
            _module_registration(
                module_name="support",
                app_id=app_id,
                module_root=root,
            ),
        )
    )
    localizer = runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=app_id,
        bot_default_locale=Locale("en"),
    )

    ru, uz = await asyncio.gather(
        asyncio.to_thread(localizer.text, "bot.greeting", locale=Locale("ru")),
        asyncio.to_thread(localizer.text, "bot.greeting", locale=Locale("uz")),
    )

    assert (ru, uz) == ("support_bot-ru", "support_bot-uz")


def test_missing_key_is_loud_in_test_and_safe_in_production() -> None:
    """Non-production surfaces catalog defects; production renders a generic safe fallback."""

    runtime = _runtime()
    runtime.initialize(())
    test_localizer = runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=BotAppId("support_bot"),
        bot_default_locale=Locale("en"),
    )
    with pytest.raises(MissingTranslationError):
        test_localizer.text("missing.key", locale=Locale("en"))

    production_runtime = LocalizationRuntime(I18nSettings(), Environment.PRODUCTION)
    production_runtime.initialize(())
    production_localizer = production_runtime.scoped_localizer(
        module_name="support",
        translation_domain="support",
        bot_app_id=BotAppId("support_bot"),
        bot_default_locale=Locale("en"),
    )
    assert production_localizer.text("missing.key", locale=Locale("en")) == (
        "Service temporarily unavailable."
    )


def test_locale_datetime_formatting_requires_timezone_aware_values() -> None:
    """Formatting helpers keep temporal output separate from translated copy."""

    from datetime import UTC, datetime

    assert format_local_datetime(datetime(2026, 8, 15, tzinfo=UTC), locale=Locale("en"))
    with pytest.raises(ValueError, match="timezone-aware"):
        format_local_datetime(datetime(2026, 8, 15), locale=Locale("en"))
