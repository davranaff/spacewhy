"""Framework-independent localization contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.core.i18n.locale import Locale


class TranslationMetrics(Protocol):
    """Observe safe, bounded-cardinality bot translation outcomes."""

    def record_bot_translation_fallback(
        self,
        *,
        bot_app_id: str,
        owner_module: str,
        locale: str,
    ) -> None:
        """Record a fallback without a user or translation-key label."""

        ...

    def record_bot_translation_missing(
        self,
        *,
        bot_app_id: str,
        owner_module: str,
        locale: str,
    ) -> None:
        """Record a missing message without a user or translation-key label."""

        ...


class ScopedLocalizer(Protocol):
    """Translate only within one module and optional bot-app ownership scope."""

    def text(
        self,
        key: str,
        *,
        locale: Locale,
        params: Mapping[str, object] | None = None,
    ) -> str:
        """Render one localized message."""

        ...

    def plural(
        self,
        singular_key: str,
        plural_key: str,
        *,
        count: int,
        locale: Locale,
        params: Mapping[str, object] | None = None,
    ) -> str:
        """Render a pluralized localized message."""

        ...
