"""Optional HTTP spans that keep tracing independent from business code."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.http.context import request_context_from_scope, route_template_from_scope
from app.core.observability.telemetry import Telemetry


class TelemetryMiddleware:
    """Create a server span when telemetry is enabled, otherwise remain a no-op."""

    def __init__(self, app: ASGIApp, *, telemetry: Telemetry) -> None:
        self.app = app
        self._telemetry = telemetry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Keep trace context active while downstream middleware handles a request."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        context = request_context_from_scope(scope)
        with self._telemetry.start_server_span(
            method=scope["method"],
            request_id=context.request_id if context is not None else None,
        ) as span:
            try:
                await self.app(scope, receive, send)
            finally:
                if span is not None:
                    span.set_attribute("http.route", route_template_from_scope(scope))
