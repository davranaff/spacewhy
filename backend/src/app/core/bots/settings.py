"""Isolated typed settings for every configured bot application."""

from __future__ import annotations

import re
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.core.bots.enums import BotProvider
from app.core.bots.ids import BotAppId
from app.core.i18n.locale import Locale

_PLACEHOLDER_SECRETS = frozenset(
    {
        "change-me",
        "example",
        "placeholder",
        "replace-with-another-secret",
        "replace-with-secret",
        "replace-with-token",
        "your-token-here",
    }
)
_WEBHOOK_SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,256}$")
_USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def _secret_fingerprint(secret: SecretStr) -> bytes:
    """Compare credentials without retaining raw values outside validation."""

    return sha256(secret.get_secret_value().encode("utf-8")).digest()


def _is_placeholder(secret: SecretStr) -> bool:
    """Reject empty and obvious documentation placeholders for enabled applications."""

    normalized = secret.get_secret_value().strip().lower()
    return normalized in _PLACEHOLDER_SECRETS | {""} or normalized.startswith("replace-with-")


def _empty_bot_apps() -> dict[BotAppId, BotAppSettings]:
    """Return a typed empty mapping for Pydantic's default factory."""

    return {}


class BotAppSettings(BaseModel):
    """Configuration that belongs to exactly one public bot application ID."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: BotProvider = BotProvider.TELEGRAM
    enabled: bool = False
    webhook_enabled: bool = True
    token: SecretStr | None = None
    webhook_secret: SecretStr | None = None
    default_locale: Locale = Locale("en")
    supported_locales: frozenset[Locale] = frozenset({Locale("en"), Locale("ru"), Locale("uz")})
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    processing_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    validate_identity_on_startup: bool = False
    expected_bot_id: int | None = Field(default=None, gt=0)
    expected_username: str | None = Field(default=None, min_length=5, max_length=32)

    @model_validator(mode="after")
    def validate_invariants(self) -> BotAppSettings:
        """Fail early without ever placing a secret value in validation text."""

        if self.default_locale not in self.supported_locales:
            raise ValueError("Bot default locale must be included in supported locales.")
        if self.expected_username is not None and not _USERNAME_PATTERN.fullmatch(
            self.expected_username
        ):
            raise ValueError("Expected bot username has an invalid format.")
        if (self.expected_bot_id is not None or self.expected_username is not None) and not (
            self.validate_identity_on_startup
        ):
            raise ValueError("Expected bot identity requires startup identity validation.")
        if not self.enabled:
            return self
        if self.token is None or _is_placeholder(self.token):
            raise ValueError("Enabled bot requires a non-placeholder token.")
        if self.webhook_enabled:
            if self.webhook_secret is None or _is_placeholder(self.webhook_secret):
                raise ValueError("Enabled webhook bot requires a non-placeholder webhook secret.")
            if not _WEBHOOK_SECRET_PATTERN.fullmatch(self.webhook_secret.get_secret_value()):
                raise ValueError("Webhook secret has an invalid format.")
        return self


class BotsSettings(BaseModel):
    """All configured bot apps, with cross-app credential isolation checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    apps: dict[BotAppId, BotAppSettings] = Field(default_factory=_empty_bot_apps)
    webhook_max_payload_bytes: int = Field(default=1_048_576, ge=1024, le=5_242_880)

    @model_validator(mode="after")
    def validate_unique_enabled_credentials(self) -> BotsSettings:
        """Reject duplicate enabled credentials without revealing either value."""

        token_owners: dict[bytes, BotAppId] = {}
        secret_owners: dict[bytes, BotAppId] = {}
        for app_id, app_settings in self.apps.items():
            if not app_settings.enabled:
                continue
            if app_settings.token is not None:
                token_fingerprint = _secret_fingerprint(app_settings.token)
                previous_owner = token_owners.get(token_fingerprint)
                if previous_owner is not None:
                    raise ValueError(
                        f"Bot app '{app_id}' duplicates the token assigned to '{previous_owner}'."
                    )
                token_owners[token_fingerprint] = app_id
            if app_settings.webhook_enabled and app_settings.webhook_secret is not None:
                secret_fingerprint = _secret_fingerprint(app_settings.webhook_secret)
                previous_owner = secret_owners.get(secret_fingerprint)
                if previous_owner is not None:
                    raise ValueError(
                        f"Bot app '{app_id}' duplicates the webhook secret assigned to "
                        f"'{previous_owner}'."
                    )
                secret_owners[secret_fingerprint] = app_id
        return self
