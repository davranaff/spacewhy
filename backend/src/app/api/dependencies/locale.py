"""FastAPI delivery dependency for the already-resolved request locale."""

from fastapi import Request

from app.core.http.context import locale_from_scope
from app.core.i18n.locale import Locale


def get_request_locale(request: Request) -> Locale:
    """Return middleware-bound locale without parsing headers in business adapters."""

    locale = locale_from_scope(request.scope)
    if locale is None:
        raise RuntimeError("HTTP locale middleware has not been configured.")
    return locale
