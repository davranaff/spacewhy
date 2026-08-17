"""Request-scoped context for transport observability."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from starlette.types import Scope

from app.core.i18n.locale import Locale

_request_context: ContextVar[RequestContext | None] = ContextVar(
    "spacewhy_request_context",
    default=None,
)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Minimal request metadata; business code receives actor context explicitly."""

    request_id: str
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    locale: Locale | None = None


def set_request_context(context: RequestContext) -> Token[RequestContext | None]:
    """Set request context for logging and return its reset token."""

    return _request_context.set(context)


def reset_request_context(token: Token[RequestContext | None]) -> None:
    """Restore the previous request context after ASGI response processing."""

    _request_context.reset(token)


def get_request_context() -> RequestContext | None:
    """Return the current request context, if this code runs inside a request."""

    return _request_context.get()


def scope_state(scope: Scope) -> dict[str, object]:
    """Return a typed mutable state mapping for technical ASGI middleware."""

    existing_state = cast(object, scope.get("state"))
    if isinstance(existing_state, dict):
        return cast(dict[str, object], existing_state)
    state: dict[str, object] = {}
    scope["state"] = state
    return state


def request_context_from_scope(scope: Scope) -> RequestContext | None:
    """Read request context attached by pure ASGI middleware."""

    context = scope_state(scope).get("request_context")
    return context if isinstance(context, RequestContext) else None


def locale_from_scope(scope: Scope) -> Locale | None:
    """Return the resolved technical locale attached by HTTP middleware."""

    context = request_context_from_scope(scope)
    return context.locale if context is not None else None


def route_template_from_scope(scope: Scope) -> str:
    """Return a matched route template without logging high-cardinality raw paths."""

    route = scope.get("route")
    route_path = getattr(route, "path_format", None)
    return route_path if isinstance(route_path, str) else "<unmatched>"
