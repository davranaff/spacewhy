"""Safe request ID creation, validation, propagation, and logging context."""

from __future__ import annotations

from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import REQUEST_ID_HEADER
from app.core.http.context import (
    RequestContext,
    reset_request_context,
    scope_state,
    set_request_context,
)

_REQUEST_ID_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode("ascii")
_MAX_REQUEST_ID_LENGTH = 64


def is_valid_request_id(value: str) -> bool:
    """Accept only canonical UUID text so headers cannot inject log content."""

    if len(value) > _MAX_REQUEST_ID_LENGTH:
        return False
    try:
        parsed = UUID(value)
    except ValueError:
        return False
    return str(parsed) == value


def request_id_from_scope(scope: Scope) -> str:
    """Use a valid incoming request ID or replace it with a generated UUID."""

    for header_name, raw_value in scope["headers"]:
        if header_name.lower() != _REQUEST_ID_HEADER_BYTES:
            continue
        value = raw_value.decode("latin-1")
        if is_valid_request_id(value):
            return value.lower()
        break
    return str(uuid4())


class RequestIdMiddleware:
    """Attach an opaque request ID before all response-producing middleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Set context and ensure every HTTP response returns the request ID."""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = request_id_from_scope(scope)
        context = RequestContext(request_id=request_id)
        state = scope_state(scope)
        state["request_context"] = context
        context_token = set_request_context(context)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                if not any(name.lower() == _REQUEST_ID_HEADER_BYTES for name, _ in headers):
                    headers.append((_REQUEST_ID_HEADER_BYTES, request_id.encode("ascii")))
                    message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            reset_request_context(context_token)
