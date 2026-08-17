"""Typed bot configuration validation and secret-isolation tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from pydantic import ValidationError as PydanticValidationError

from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotAppSettings, BotsSettings
from app.core.config.environment import Environment
from app.core.config.settings import AppSettings, Settings
from app.core.i18n.locale import Locale

_DEFAULT_BOT_LOCALE = Locale("en")
_DEFAULT_BOT_LOCALES = frozenset({Locale("en"), Locale("ru"), Locale("uz")})


def _enabled_bot(
    *,
    token: str = "test-token-a",
    webhook_secret: str = "test_webhook_secret_a",
    default_locale: Locale = _DEFAULT_BOT_LOCALE,
    supported_locales: frozenset[Locale] = _DEFAULT_BOT_LOCALES,
    expected_bot_id: int | None = None,
    request_timeout_seconds: float = 10.0,
) -> BotAppSettings:
    """Return valid fake credentials that never pass to the real Telegram factory."""

    return BotAppSettings(
        enabled=True,
        token=SecretStr(token),
        webhook_secret=SecretStr(webhook_secret),
        default_locale=default_locale,
        supported_locales=supported_locales,
        expected_bot_id=expected_bot_id,
        request_timeout_seconds=request_timeout_seconds,
    )


def test_nested_environment_parses_two_isolated_bot_apps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic Settings preserves per-app credentials and locale settings."""

    monkeypatch.setenv("BOTS__APPS__SUPPORT_BOT__ENABLED", "true")
    monkeypatch.setenv("BOTS__APPS__SUPPORT_BOT__TOKEN", "test-token-a")
    monkeypatch.setenv("BOTS__APPS__SUPPORT_BOT__WEBHOOK_SECRET", "test_webhook_secret_a")
    monkeypatch.setenv("BOTS__APPS__SUPPORT_BOT__DEFAULT_LOCALE", "ru")
    monkeypatch.setenv("BOTS__APPS__SUPPORT_BOT__SUPPORTED_LOCALES", '["ru","uz","en"]')
    monkeypatch.setenv("BOTS__APPS__SALES_ASSISTANT__ENABLED", "true")
    monkeypatch.setenv("BOTS__APPS__SALES_ASSISTANT__TOKEN", "test-token-b")
    monkeypatch.setenv("BOTS__APPS__SALES_ASSISTANT__WEBHOOK_SECRET", "test_webhook_secret_b")
    monkeypatch.setenv("BOTS__APPS__SALES_ASSISTANT__DEFAULT_LOCALE", "uz")
    monkeypatch.setenv("BOTS__APPS__SALES_ASSISTANT__SUPPORTED_LOCALES", '["uz","ru","en"]')

    settings = Settings()

    assert set(settings.bots.apps) == {BotAppId("support_bot"), BotAppId("sales_assistant")}
    assert settings.bots.apps[BotAppId("support_bot")].default_locale == Locale("ru")
    assert settings.bots.apps[BotAppId("sales_assistant")].default_locale == Locale("uz")
    assert (
        settings.bots.apps[BotAppId("support_bot")].token
        != settings.bots.apps[BotAppId("sales_assistant")].token
    )


def test_enabled_bot_requires_non_placeholder_token_and_webhook_secret() -> None:
    """Enabled apps fail before traffic when either secret is absent or a placeholder."""

    with pytest.raises(PydanticValidationError, match="non-placeholder token"):
        BotAppSettings(enabled=True, webhook_secret=SecretStr("test_webhook_secret_a"))
    with pytest.raises(PydanticValidationError, match="non-placeholder webhook secret"):
        BotAppSettings(enabled=True, token=SecretStr("test-token-a"))
    with pytest.raises(PydanticValidationError, match="non-placeholder token"):
        BotAppSettings(
            enabled=True,
            token=SecretStr("replace-with-secret"),
            webhook_secret=SecretStr("test_webhook_secret_a"),
        )


def test_disabled_bot_may_omit_credentials() -> None:
    """Configuration can predeclare a disabled app without secret material."""

    disabled = BotAppSettings(enabled=False, token=None, webhook_secret=None)

    assert not disabled.enabled
    assert disabled.token is None
    assert disabled.webhook_secret is None


def test_duplicate_enabled_tokens_and_webhook_secrets_are_rejected_without_values() -> None:
    """Cross-app uniqueness validation names app IDs but never renders credentials."""

    token = "test-duplicate-token"
    secret = "test_duplicate_secret"
    with pytest.raises(PydanticValidationError) as token_error:
        BotsSettings(
            apps={
                BotAppId("support_bot"): _enabled_bot(token=token, webhook_secret=secret),
                BotAppId("sales_assistant"): _enabled_bot(
                    token=token,
                    webhook_secret="test_webhook_secret_b",
                ),
            }
        )
    assert "support_bot" in str(token_error.value)
    assert token not in str(token_error.value)

    with pytest.raises(PydanticValidationError) as secret_error:
        BotsSettings(
            apps={
                BotAppId("support_bot"): _enabled_bot(webhook_secret=secret),
                BotAppId("sales_assistant"): _enabled_bot(
                    token="test-token-b",
                    webhook_secret=secret,
                ),
            }
        )
    assert "support_bot" in str(secret_error.value)
    assert secret not in str(secret_error.value)


def test_bot_app_id_and_locale_invariants_are_strict() -> None:
    """Unsafe route identifiers and unsupported defaults are rejected."""

    with pytest.raises(ValueError, match="lowercase ASCII"):
        BotAppId("../support")
    with pytest.raises(PydanticValidationError, match="default locale"):
        _enabled_bot(
            default_locale=Locale("fr"),
            supported_locales=frozenset({Locale("en"), Locale("ru")}),
        )
    with pytest.raises(PydanticValidationError, match="outside I18N"):
        Settings(
            bots=BotsSettings(
                apps={
                    BotAppId("support_bot"): _enabled_bot(
                        supported_locales=frozenset({Locale("en"), Locale("fr")})
                    )
                }
            )
        )


def test_identity_and_timeout_configuration_is_validated() -> None:
    """Identity expectations cannot be inert and timeouts stay bounded."""

    with pytest.raises(PydanticValidationError, match="identity requires"):
        _enabled_bot(expected_bot_id=123)
    with pytest.raises(PydanticValidationError):
        _enabled_bot(request_timeout_seconds=0)


def test_bot_secrets_are_masked_in_repr_and_validation_errors() -> None:
    """Tokens and webhook secrets never leak through ordinary settings diagnostics."""

    token = "test-private-token"
    secret = "test_private_webhook_secret"
    settings = _enabled_bot(token=token, webhook_secret=secret)

    assert token not in repr(settings)
    assert secret not in repr(settings)
    with pytest.raises(PydanticValidationError) as error:
        Settings(
            app=AppSettings(environment=Environment.PRODUCTION),
            bots=BotsSettings(apps={BotAppId("support_bot"): settings}),
        )
    assert token not in str(error.value)
    assert secret not in str(error.value)
