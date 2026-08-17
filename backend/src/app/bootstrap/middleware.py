"""Deliberate, pure-ASGI middleware registration order."""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.bootstrap.container import AppContainer
from app.core.http.middleware import (
    AccessLogMiddleware,
    LocaleMiddleware,
    RequestIdMiddleware,
    RequestTimingMiddleware,
    TelemetryMiddleware,
)


def register_middleware(app: FastAPI, container: AppContainer) -> None:
    """Register middleware in reverse order of the inbound request path.

    Inbound processing is Request ID, locale, optional trusted proxy headers, trusted host,
    CORS, telemetry, access log, request timing, then the application. Request ID is
    deliberately outermost so preflight and rejected requests are correlated too.
    """

    security = container.settings.security
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(TelemetryMiddleware, telemetry=container.telemetry)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(security.cors_allowed_origins),
        allow_credentials=security.cors_allow_credentials,
        allow_methods=list(security.cors_allowed_methods),
        allow_headers=list(security.cors_allowed_headers),
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(security.trusted_hosts))
    if security.proxy_headers_enabled:
        app.add_middleware(
            ProxyHeadersMiddleware,
            trusted_hosts=list(security.trusted_proxy_hosts),
        )
    app.add_middleware(LocaleMiddleware, settings=container.settings.i18n)
    app.add_middleware(RequestIdMiddleware)
