"""Deterministic locale resolution for HTTP requests and bot updates."""

from __future__ import annotations

from collections.abc import Iterable

from app.core.i18n.locale import Locale


def parse_accept_language(
    value: str | None,
    *,
    supported_locales: frozenset[Locale],
    max_length: int,
) -> Locale | None:
    """Safely select the highest-ranked supported locale from one bounded header."""

    if value is None or len(value) > max_length:
        return None
    candidates: list[tuple[float, int, Locale]] = []
    for index, raw_candidate in enumerate(value.split(",")):
        language_range, _, raw_parameters = raw_candidate.strip().partition(";")
        if not language_range or language_range == "*":
            continue
        quality = 1.0
        if raw_parameters:
            for parameter in raw_parameters.split(";"):
                name, separator, raw_quality = parameter.strip().partition("=")
                if name.lower() != "q" or not separator:
                    continue
                try:
                    quality = float(raw_quality)
                except ValueError:
                    quality = 0.0
        if quality <= 0 or quality > 1:
            continue
        try:
            locale = Locale.parse(language_range)
        except (TypeError, ValueError):
            continue
        if locale in supported_locales:
            candidates.append((quality, index, locale))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[0], item[1]))[0][2]


def resolve_http_locale(
    *,
    supported_locales: frozenset[Locale],
    default_locale: Locale,
    user_locale: Locale | None = None,
    request_locale: Locale | None = None,
    accept_language: str | None = None,
    accept_language_max_length: int = 512,
) -> Locale:
    """Resolve HTTP locale with explicit preferences before transport hints."""

    for candidate in (user_locale, request_locale):
        if candidate is not None and candidate in supported_locales:
            return candidate
    header_locale = parse_accept_language(
        accept_language,
        supported_locales=supported_locales,
        max_length=accept_language_max_length,
    )
    return header_locale or default_locale


def resolve_bot_locale(
    *,
    supported_locales: frozenset[Locale],
    bot_default_locale: Locale,
    global_default_locale: Locale,
    stored_user_locale: Locale | None = None,
    conversation_locale: Locale | None = None,
    provider_language_code: str | None = None,
) -> Locale:
    """Resolve bot locale without storing mutable state in the process."""

    for candidate in (stored_user_locale, conversation_locale):
        if candidate is not None and candidate in supported_locales:
            return candidate
    if provider_language_code is not None:
        try:
            provider_locale = Locale.parse(provider_language_code)
        except (TypeError, ValueError):
            provider_locale = None
        if provider_locale is not None and provider_locale in supported_locales:
            return provider_locale
    if bot_default_locale in supported_locales:
        return bot_default_locale
    return global_default_locale


def locale_fallbacks(
    requested_locale: Locale,
    *,
    bot_default_locale: Locale | None,
    global_default_locale: Locale,
) -> tuple[Locale, ...]:
    """Return a stable deduplicated fallback sequence within one localizer scope."""

    candidates: Iterable[Locale | None] = (
        requested_locale,
        bot_default_locale,
        global_default_locale,
    )
    result: list[Locale] = []
    for candidate in candidates:
        if candidate is not None and candidate not in result:
            result.append(candidate)
    return tuple(result)
