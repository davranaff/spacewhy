"""Request-scoped HTTP locale resolution without global mutable state."""

from __future__ import annotations

from dataclasses import replace

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config.settings import I18nSettings
from app.core.http.context import (
    RequestContext,
    request_context_from_scope,
    reset_request_context,
    scope_state,
    set_request_context,
)
from app.core.i18n.resolver import resolve_http_locale

_ACCEPT_LANGUAGE_HEADER = b"accept-language"
_CONTENT_LANGUAGE_HEADER = b"content-language"


class LocaleMiddleware:
    """Resolve one locale after request ID setup and restore it after the response."""

    def __init__(self, app: ASGIApp, *, settings: I18nSettings) -> None:
        self.app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind an immutable locale context to this HTTP request only."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        accept_language = self._accept_language(scope)
        locale = resolve_http_locale(
            supported_locales=self._settings.supported_locales,
            default_locale=self._settings.default_locale,
            accept_language=accept_language,
            accept_language_max_length=self._settings.accept_language_max_length,
        )
        previous_context = request_context_from_scope(scope)
        context = (
            replace(previous_context, locale=locale)
            if previous_context is not None
            else RequestContext(request_id="unavailable", locale=locale)
        )
        scope_state(scope)["request_context"] = context
        context_token = set_request_context(context)

        async def send_with_content_language(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                if not any(name.lower() == _CONTENT_LANGUAGE_HEADER for name, _ in headers):
                    headers.append((_CONTENT_LANGUAGE_HEADER, str(locale).encode("ascii")))
                    message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_content_language)
        finally:
            reset_request_context(context_token)

    @staticmethod
    def _accept_language(scope: Scope) -> str | None:
        """Return the first bounded header value without decoding untrusted bytes as UTF-8."""

        for name, value in scope["headers"]:
            if name.lower() == _ACCEPT_LANGUAGE_HEADER:
                return value.decode("latin-1")
        return None
