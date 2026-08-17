"""Babel/gettext PO catalog loading, compilation, and cross-locale validation."""

from __future__ import annotations

from collections.abc import Iterable
from gettext import GNUTranslations
from io import BytesIO
from typing import Any, cast

from babel.messages import mofile, pofile

from app.core.i18n.catalog import CatalogMessage, CatalogSource, LoadedCatalog
from app.core.i18n.errors import CatalogValidationError
from app.core.i18n.locale import Locale
from app.core.i18n.validation import duplicate_message_ids, validate_placeholder_parity


class CatalogLoader:
    """Load only explicitly registered gettext catalogs into an immutable runtime."""

    def load(self, sources: Iterable[CatalogSource]) -> tuple[LoadedCatalog, ...]:
        """Load every declared source and validate each ownership scope independently."""

        loaded: list[LoadedCatalog] = []
        for source in sources:
            source_catalogs = tuple(
                self._load_one(source, locale) for locale in sorted(source.locales, key=str)
            )
            self._validate_locale_coverage(source_catalogs)
            loaded.extend(source_catalogs)
        return tuple(loaded)

    def _load_one(self, source: CatalogSource, locale: Locale) -> LoadedCatalog:
        """Parse and compile one PO source using Babel and GNU gettext."""

        path = source.path_for(locale)
        if not path.is_file():
            raise CatalogValidationError(
                f"Missing catalog for scope '{source.scope.domain}' and locale '{locale}'."
            )
        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise CatalogValidationError("Translation catalog cannot be read.") from error
        duplicates = duplicate_message_ids(raw_text)
        if duplicates:
            rendered = ", ".join(sorted(duplicates))
            raise CatalogValidationError(
                f"Translation catalog contains duplicate keys: {rendered}."
            )
        try:
            with path.open("r", encoding="utf-8") as catalog_file:
                babel_catalog = pofile.read_po(
                    catalog_file,
                    locale=str(locale),
                    domain=source.scope.domain,
                    abort_invalid=True,
                )
        except (OSError, UnicodeError, ValueError) as error:
            raise CatalogValidationError(
                f"Translation catalog is malformed for scope '{source.scope.domain}'."
            ) from error
        messages = self._messages_from_babel_catalog(babel_catalog)
        compiled = BytesIO()
        try:
            mofile.write_mo(compiled, babel_catalog)
            translations = GNUTranslations(BytesIO(compiled.getvalue()))
        except (OSError, ValueError) as error:
            raise CatalogValidationError(
                f"Translation catalog cannot be compiled for scope '{source.scope.domain}'."
            ) from error
        return LoadedCatalog(
            scope=source.scope,
            locale=locale,
            messages=messages,
            translations=translations,
        )

    def _messages_from_babel_catalog(self, babel_catalog: Any) -> dict[str, CatalogMessage]:
        """Build metadata and reject missing strings or malformed plural entries."""

        messages: dict[str, CatalogMessage] = {}
        for raw_message in babel_catalog:
            message_id: object = raw_message.id
            if not message_id:
                continue
            if isinstance(message_id, tuple):
                plural_id = cast(tuple[object, ...], message_id)
                if len(plural_id) != 2:
                    raise CatalogValidationError("Translation catalog contains an invalid plural.")
                singular_key = plural_id[0]
                plural_key = plural_id[1]
                translations: object = raw_message.string
                if (
                    not isinstance(singular_key, str)
                    or not isinstance(plural_key, str)
                    or not isinstance(translations, tuple)
                    or not translations
                ):
                    raise CatalogValidationError("Translation catalog contains an invalid plural.")
                translation_items = cast(tuple[object, ...], translations)
                if not all(isinstance(item, str) and item for item in translation_items):
                    raise CatalogValidationError("Translation catalog contains an invalid plural.")
                templates = tuple(cast(str, item) for item in translation_items)
                message = CatalogMessage(
                    key=singular_key,
                    plural_key=plural_key,
                    templates=templates,
                )
            else:
                translation: object = raw_message.string
                if not isinstance(message_id, str) or not isinstance(translation, str):
                    raise CatalogValidationError("Translation catalog contains an invalid message.")
                if not translation:
                    raise CatalogValidationError(
                        f"Translation catalog is missing a value for key '{message_id}'."
                    )
                message = CatalogMessage(
                    key=message_id,
                    plural_key=None,
                    templates=(translation,),
                )
            if message.key in messages:
                raise CatalogValidationError(
                    f"Translation catalog contains duplicate key '{message.key}'."
                )
            messages[message.key] = message
        if not messages:
            raise CatalogValidationError("Translation catalog must contain at least one message.")
        return messages

    def _validate_locale_coverage(self, catalogs: tuple[LoadedCatalog, ...]) -> None:
        """Require key, plural, and placeholder parity for every owned source."""

        if not catalogs:
            raise CatalogValidationError("Translation catalog source has no locales.")
        reference = catalogs[0]
        reference_keys = set(reference.messages)
        parity_templates: list[tuple[str, tuple[str, ...]]] = []
        for catalog in catalogs:
            keys = set(catalog.messages)
            if keys != reference_keys:
                raise CatalogValidationError(
                    f"Translation key coverage differs for scope '{catalog.scope.domain}'."
                )
            for key, message in catalog.messages.items():
                reference_message = reference.messages[key]
                if message.plural_key != reference_message.plural_key:
                    raise CatalogValidationError(
                        f"Translation plural contract differs for key '{key}'."
                    )
                parity_templates.append((key, message.templates))
        validate_placeholder_parity(parity_templates)
