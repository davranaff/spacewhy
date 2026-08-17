"""Typed global internationalization settings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.i18n.locale import Locale


class I18nSettings(BaseModel):
    """Global supported locales and HTTP parsing limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_locale: Locale = Locale("en")
    supported_locales: frozenset[Locale] = frozenset(
        {
            Locale("en"),
            Locale("ru"),
            Locale("uz"),
        }
    )
    accept_language_max_length: int = Field(default=512, ge=64, le=4096)

    @model_validator(mode="after")
    def validate_default_locale(self) -> I18nSettings:
        """Keep fallback behavior deterministic."""

        if self.default_locale not in self.supported_locales:
            raise ValueError("I18N__DEFAULT_LOCALE must be included in supported locales.")
        return self
