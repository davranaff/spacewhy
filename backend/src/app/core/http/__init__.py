"""HTTP context and transport-level technical contracts."""

from app.core.http.context import RequestContext, get_request_context

__all__ = ["RequestContext", "get_request_context"]
