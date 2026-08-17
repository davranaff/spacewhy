"""Scoped localizers that prevent cross-module and cross-bot fallback."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from app.core.bots.ids import BotAppId
from app.core.config.environment import Environment
from app.core.i18n.catalog import CatalogSource, CatalogStore, TranslationScope
from app.core.i18n.contracts import TranslationMetrics
from app.core.i18n.errors import CatalogValidationError, MissingTranslationError
from app.core.i18n.loader import CatalogLoader
from app.core.i18n.locale import Locale
from app.core.i18n.resolver import locale_fallbacks
from app.core.i18n.settings import I18nSettings
from app.core.i18n.validation import interpolate

logger = logging.getLogger("spacewhy")

_CORE_SCOPE = TranslationScope(module_name=None, bot_app_id=None, domain="platform")


@dataclass(frozen=True, slots=True)
class ModuleCatalogRegistration:
    """A module-owned catalog directory declared alongside a bot registration."""

    module_name: str
    bot_app_id: BotAppId
    translation_domain: str
    module_root: Path
    supported_locales: frozenset[Locale]

    def sources(self) -> tuple[CatalogSource, CatalogSource]:
        """Return common and app-specific catalogs without scanning other modules."""

        common_scope = TranslationScope(
            module_name=self.module_name,
            bot_app_id=None,
            domain=self.translation_domain,
        )
        bot_scope = TranslationScope(
            module_name=self.module_name,
            bot_app_id=self.bot_app_id,
            domain=self.translation_domain,
        )
        return (
            CatalogSource(
                scope=common_scope,
                root=self.module_root / "locales" / "common",
                filename="messages.po",
                locales=self.supported_locales,
            ),
            CatalogSource(
                scope=bot_scope,
                root=self.module_root / "locales" / "bots" / str(self.bot_app_id),
                filename="messages.po",
                locales=self.supported_locales,
            ),
        )


class LocalizationRuntime:
    """Own loaded gettext catalogs and create only pre-bound localizers."""

    def __init__(
        self,
        settings: I18nSettings,
        environment: Environment,
        metrics: TranslationMetrics | None = None,
    ) -> None:
        self._settings = settings
        self._environment = environment
        self._metrics = metrics
        self._catalogs: CatalogStore | None = None

    @property
    def is_initialized(self) -> bool:
        """Return whether catalogs passed startup validation."""

        return self._catalogs is not None

    def initialize(self, module_catalogs: Sequence[ModuleCatalogRegistration]) -> None:
        """Load core and explicitly registered module-owned catalogs exactly once."""

        if self._catalogs is not None:
            return
        core_root = Path(__file__).parent / "locales"
        self._validate_catalog_layout(core_root, module_catalogs)
        sources: list[CatalogSource] = [
            CatalogSource(
                scope=_CORE_SCOPE,
                root=core_root,
                filename="platform.po",
                locales=self._settings.supported_locales,
            )
        ]
        sources_by_scope: dict[TranslationScope, CatalogSource] = {}
        for registration in module_catalogs:
            for source in registration.sources():
                existing = sources_by_scope.get(source.scope)
                if existing is None:
                    sources_by_scope[source.scope] = source
                    continue
                if existing.root != source.root or existing.filename != source.filename:
                    raise ValueError(
                        f"Translation scope '{source.scope.domain}' has conflicting catalog roots."
                    )
                sources_by_scope[source.scope] = CatalogSource(
                    scope=source.scope,
                    root=source.root,
                    filename=source.filename,
                    locales=existing.locales | source.locales,
                )
        sources.extend(sources_by_scope.values())
        self._catalogs = CatalogStore(CatalogLoader().load(sources))

    def _validate_catalog_layout(
        self,
        core_root: Path,
        module_catalogs: Sequence[ModuleCatalogRegistration],
    ) -> None:
        """Reject unowned app directories and unsupported locales before catalog loading."""

        self._validate_locale_directories(
            root=core_root,
            supported_locales=self._settings.supported_locales,
            scope_name="core platform",
        )
        registrations_by_module: dict[tuple[str, Path], list[ModuleCatalogRegistration]] = {}
        roots_by_module: dict[str, Path] = {}
        for registration in module_catalogs:
            existing_root = roots_by_module.setdefault(
                registration.module_name,
                registration.module_root,
            )
            if existing_root != registration.module_root:
                raise CatalogValidationError(
                    f"Module '{registration.module_name}' has conflicting catalog roots."
                )
            registrations_by_module.setdefault(
                (registration.module_name, registration.module_root),
                [],
            ).append(registration)
        for (module_name, module_root), registrations in registrations_by_module.items():
            domains = {registration.translation_domain for registration in registrations}
            if len(domains) != 1:
                raise CatalogValidationError(
                    f"Module '{module_name}' has conflicting translation domains."
                )
            supported_by_app: dict[BotAppId, frozenset[Locale]] = {}
            common_locale_values: set[Locale] = set()
            for registration in registrations:
                supported_by_app[registration.bot_app_id] = registration.supported_locales
                common_locale_values.update(registration.supported_locales)
            common_locales = frozenset(common_locale_values)
            locales_root = module_root / "locales"
            self._validate_locale_directories(
                root=locales_root / "common",
                supported_locales=common_locales,
                scope_name=f"module '{module_name}' common",
            )
            bots_root = locales_root / "bots"
            if not bots_root.exists():
                continue
            if not bots_root.is_dir():
                raise CatalogValidationError(
                    f"Bot catalog root for module '{module_name}' must be a directory."
                )
            try:
                app_directories = tuple(bots_root.iterdir())
            except OSError as error:
                raise CatalogValidationError(
                    f"Bot catalog root for module '{module_name}' cannot be read."
                ) from error
            for app_directory in app_directories:
                if not app_directory.is_dir():
                    raise CatalogValidationError(
                        f"Bot catalog root for module '{module_name}' contains an invalid entry."
                    )
                try:
                    app_id = BotAppId(app_directory.name)
                except (TypeError, ValueError) as error:
                    raise CatalogValidationError(
                        f"Bot catalog root for module '{module_name}' contains an invalid app ID."
                    ) from error
                app_locales = supported_by_app.get(app_id)
                if app_locales is None:
                    raise CatalogValidationError(
                        f"Bot catalog directory '{app_id}' is not registered by module "
                        f"'{module_name}'."
                    )
                self._validate_locale_directories(
                    root=app_directory,
                    supported_locales=app_locales,
                    scope_name=f"bot app '{app_id}'",
                )

    @staticmethod
    def _validate_locale_directories(
        *,
        root: Path,
        supported_locales: frozenset[Locale],
        scope_name: str,
    ) -> None:
        """Ensure discovered locale paths belong to an explicitly supported scope."""

        if not root.exists():
            return
        if not root.is_dir():
            raise CatalogValidationError(f"Catalog root for {scope_name} must be a directory.")
        try:
            entries = tuple(root.iterdir())
        except OSError as error:
            raise CatalogValidationError(
                f"Catalog root for {scope_name} cannot be read."
            ) from error
        for entry in entries:
            if not entry.is_dir():
                raise CatalogValidationError(
                    f"Catalog root for {scope_name} contains an invalid locale entry."
                )
            try:
                locale = Locale.parse(entry.name)
            except (TypeError, ValueError) as error:
                raise CatalogValidationError(
                    f"Catalog root for {scope_name} contains an invalid locale."
                ) from error
            if locale not in supported_locales:
                raise CatalogValidationError(
                    f"Catalog root for {scope_name} contains unsupported locale '{locale}'."
                )

    def shutdown(self) -> None:
        """Drop catalog references so repeated app factories stay isolated."""

        self._catalogs = None

    def scoped_localizer(
        self,
        *,
        module_name: str,
        translation_domain: str,
        bot_app_id: BotAppId | None,
        bot_default_locale: Locale | None,
    ) -> BoundLocalizer:
        """Return a localizer unable to select another module or bot scope."""

        if self._catalogs is None:
            raise RuntimeError("Localization runtime has not been initialized.")
        return BoundLocalizer(
            catalogs=self._catalogs,
            module_name=module_name,
            translation_domain=translation_domain,
            bot_app_id=bot_app_id,
            bot_default_locale=bot_default_locale,
            global_default_locale=self._settings.default_locale,
            production=self._environment.is_production,
            metrics=self._metrics,
        )

    def core_localizer(self) -> BoundLocalizer:
        """Return a localizer limited to generic platform translations."""

        if self._catalogs is None:
            raise RuntimeError("Localization runtime has not been initialized.")
        return BoundLocalizer(
            catalogs=self._catalogs,
            module_name=None,
            translation_domain="platform",
            bot_app_id=None,
            bot_default_locale=None,
            global_default_locale=self._settings.default_locale,
            production=self._environment.is_production,
            metrics=self._metrics,
        )


@dataclass(frozen=True, slots=True)
class BoundLocalizer:
    """Concrete scoped localizer with deterministic, non-crossing fallback."""

    catalogs: CatalogStore
    module_name: str | None
    translation_domain: str
    bot_app_id: BotAppId | None
    bot_default_locale: Locale | None
    global_default_locale: Locale
    production: bool
    metrics: TranslationMetrics | None

    def text(
        self,
        key: str,
        *,
        locale: Locale,
        params: Mapping[str, object] | None = None,
    ) -> str:
        """Resolve and safely interpolate a singular translated template."""

        template = self._resolve_text(key, locale)
        return interpolate(template, dict(params or {}))

    def plural(
        self,
        singular_key: str,
        plural_key: str,
        *,
        count: int,
        locale: Locale,
        params: Mapping[str, object] | None = None,
    ) -> str:
        """Resolve a scoped plural form and require an explicit count parameter."""

        for candidate_locale in self._fallbacks(locale):
            for scope_index, scope in enumerate(self._scopes_for_key(singular_key)):
                catalog = self.catalogs.get(scope, candidate_locale)
                if catalog is None:
                    continue
                template = catalog.plural(singular_key, plural_key, count)
                if template is not None:
                    rendered_params = dict(params or {})
                    rendered_params.setdefault("count", count)
                    self._record_fallback_if_needed(
                        requested_locale=locale,
                        resolved_locale=candidate_locale,
                        scope_index=scope_index,
                    )
                    return interpolate(template, rendered_params)
        return self._missing(singular_key, locale)

    def _resolve_text(self, key: str, locale: Locale) -> str:
        for candidate_locale in self._fallbacks(locale):
            for scope_index, scope in enumerate(self._scopes_for_key(key)):
                catalog = self.catalogs.get(scope, candidate_locale)
                if catalog is None:
                    continue
                template = catalog.text(key)
                if template is not None:
                    self._record_fallback_if_needed(
                        requested_locale=locale,
                        resolved_locale=candidate_locale,
                        scope_index=scope_index,
                    )
                    return template
        return self._missing(key, locale)

    def _fallbacks(self, locale: Locale) -> tuple[Locale, ...]:
        return locale_fallbacks(
            locale,
            bot_default_locale=self.bot_default_locale,
            global_default_locale=self.global_default_locale,
        )

    def _scopes_for_key(self, key: str) -> tuple[TranslationScope, ...]:
        if self.module_name is None:
            return (_CORE_SCOPE,) if key.startswith("platform.") else ()
        scopes: list[TranslationScope] = []
        if self.bot_app_id is not None:
            scopes.append(
                TranslationScope(
                    module_name=self.module_name,
                    bot_app_id=self.bot_app_id,
                    domain=self.translation_domain,
                )
            )
        scopes.append(
            TranslationScope(
                module_name=self.module_name,
                bot_app_id=None,
                domain=self.translation_domain,
            )
        )
        if key.startswith("platform."):
            scopes.append(_CORE_SCOPE)
        return tuple(scopes)

    def _missing(self, key: str, locale: Locale) -> str:
        if (
            self.metrics is not None
            and self.bot_app_id is not None
            and self.module_name is not None
        ):
            self.metrics.record_bot_translation_missing(
                bot_app_id=str(self.bot_app_id),
                owner_module=self.module_name,
                locale=str(locale),
            )
        if not self.production:
            raise MissingTranslationError(
                f"Missing translation key '{key}' for module '{self.module_name}' "
                f"and locale '{locale}'."
            )
        logger.warning(
            "translation_missing",
            extra={
                "owner_module": self.module_name,
                "bot_app_id": self.bot_app_id,
                "locale": str(locale),
                "translation_key": key,
            },
        )
        fallback_catalog = self.catalogs.get(_CORE_SCOPE, self.global_default_locale)
        if fallback_catalog is None:
            return "Service temporarily unavailable."
        fallback_template = fallback_catalog.text("platform.temporary_unavailable")
        return fallback_template or "Service temporarily unavailable."

    def _record_fallback_if_needed(
        self,
        *,
        requested_locale: Locale,
        resolved_locale: Locale,
        scope_index: int,
    ) -> None:
        """Emit a bounded metric only when an owned scope or locale fallback was used."""

        if (
            self.metrics is not None
            and self.bot_app_id is not None
            and self.module_name is not None
            and (requested_locale != resolved_locale or scope_index > 0)
        ):
            self.metrics.record_bot_translation_fallback(
                bot_app_id=str(self.bot_app_id),
                owner_module=self.module_name,
                locale=str(resolved_locale),
            )
