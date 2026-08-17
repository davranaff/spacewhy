"""Structured, body-free access logging."""

from __future__ import annotations

import logging
from typing import cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.http.context import (
    request_context_from_scope,
    route_template_from_scope,
    scope_state,
)

logger = logging.getLogger("spacewhy")


class AccessLogMiddleware:
    """Log safe request completion metadata after the response has been produced."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Capture response status without inspecting body content."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_status: int | None = None

        async def capture_status(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = cast(int, message["status"])
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            context = request_context_from_scope(scope)
            duration_value = scope_state(scope).get("duration_ms")
            duration_ms = float(duration_value) if isinstance(duration_value, int | float) else None
            logger.info(
                "http_request_completed",
                extra={
                    "request_id": context.request_id if context is not None else None,
                    "http_method": scope["method"],
                    "route": route_template_from_scope(scope),
                    "status_code": response_status or 500,
                    "duration_ms": duration_ms,
                    "locale": str(context.locale)
                    if context is not None and context.locale
                    else None,
                },
            )
