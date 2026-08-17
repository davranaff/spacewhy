"""Immutable catalog scopes and gettext-backed catalog storage."""

from __future__ import annotations

from dataclasses import dataclass
from gettext import GNUTranslations
from pathlib import Path

from app.core.bots.ids import BotAppId
from app.core.i18n.locale import Locale


@dataclass(frozen=True, slots=True)
class TranslationScope:
    """The only ownership scope from which a localizer may resolve messages."""

    module_name: str | None
    bot_app_id: BotAppId | None
    domain: str


@dataclass(frozen=True, slots=True)
class CatalogSource:
    """One owned catalog directory and its required locale coverage."""

    scope: TranslationScope
    root: Path
    filename: str
    locales: frozenset[Locale]

    def path_for(self, locale: Locale) -> Path:
        """Return the deterministic gettext PO location for one locale."""

        return self.root / str(locale) / self.filename


@dataclass(frozen=True, slots=True)
class CatalogMessage:
    """Metadata used for safe key and placeholder validation."""

    key: str
    plural_key: str | None
    templates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadedCatalog:
    """A validated gettext catalog for one scope and normalized locale."""

    scope: TranslationScope
    locale: Locale
    messages: dict[str, CatalogMessage]
    translations: GNUTranslations

    def text(self, key: str) -> str | None:
        """Return a translated template only when the semantic key exists."""

        if key not in self.messages:
            return None
        return self.translations.gettext(key)

    def plural(self, singular_key: str, plural_key: str, count: int) -> str | None:
        """Return a plural template only when the declared plural pair matches."""

        message = self.messages.get(singular_key)
        if message is None or message.plural_key != plural_key:
            return None
        return self.translations.ngettext(singular_key, plural_key, count)


class CatalogStore:
    """Private immutable lookup table shared only by scoped localizers."""

    def __init__(self, catalogs: tuple[LoadedCatalog, ...]) -> None:
        by_scope_locale: dict[tuple[TranslationScope, Locale], LoadedCatalog] = {}
        for catalog in catalogs:
            key = (catalog.scope, catalog.locale)
            if key in by_scope_locale:
                raise ValueError("Duplicate translation catalog scope and locale.")
            by_scope_locale[key] = catalog
        self._catalogs = by_scope_locale

    def get(self, scope: TranslationScope, locale: Locale) -> LoadedCatalog | None:
        """Return a catalog without widening its translation scope."""

        return self._catalogs.get((scope, locale))
