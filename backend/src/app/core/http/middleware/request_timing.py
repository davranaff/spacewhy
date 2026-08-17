"""Low-overhead pure ASGI request timing."""

from __future__ import annotations

from time import perf_counter

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.http.context import scope_state


class RequestTimingMiddleware:
    """Record elapsed time without reading or buffering request/response bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Store elapsed milliseconds after downstream processing completes."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        try:
            await self.app(scope, receive, send)
        finally:
            state = scope_state(scope)
            state["duration_ms"] = round((perf_counter() - started_at) * 1000, 3)
