"""Private Telegram webhook endpoint with bounded body and exact runtime routing."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from starlette.responses import Response

from app.bootstrap.bot_apps import WebhookDispatchResult
from app.bootstrap.container import get_container_from_app
from app.core.bots.ids import BotAppId
from app.core.bots.settings import BotsSettings
from app.core.http.context import request_context_from_scope

router = APIRouter()

_TELEGRAM_SECRET_HEADER = "x-telegram-bot-api-secret-token"


@router.post(
    "/webhooks/telegram/{raw_bot_app_id}",
    include_in_schema=False,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def telegram_webhook(raw_bot_app_id: str, request: Request) -> Response:
    """Verify and dispatch one Telegram update to its exact app runtime."""

    try:
        app_id = BotAppId(raw_bot_app_id)
    except (TypeError, ValueError):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    container = get_container_from_app(request.app)
    if not _is_json_content_type(request.headers.get("content-type")):
        return Response(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
    if _content_length_exceeds(request.headers.get("content-length"), container.settings.bots):
        return Response(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    payload = await _read_bounded_body(request, container.settings.bots.webhook_max_payload_bytes)
    if payload is None:
        return Response(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    request_context = request_context_from_scope(request.scope)
    result = await container.bot_platform.dispatch_telegram(
        app_id,
        presented_secret=request.headers.get(_TELEGRAM_SECRET_HEADER),
        payload=payload,
        request_id=request_context.request_id if request_context is not None else "unavailable",
    )
    if result is WebhookDispatchResult.ACCEPTED:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if result in {WebhookDispatchResult.NOT_FOUND, WebhookDispatchResult.REJECTED}:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    if result is WebhookDispatchResult.MALFORMED:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    if result is WebhookDispatchResult.TIMED_OUT:
        return Response(status_code=status.HTTP_504_GATEWAY_TIMEOUT)
    return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


def _is_json_content_type(content_type: str | None) -> bool:
    """Accept JSON with optional parameters and reject all other webhook bodies."""

    return content_type is not None and content_type.split(";", maxsplit=1)[0].strip().lower() == (
        "application/json"
    )


def _content_length_exceeds(content_length: str | None, settings: BotsSettings) -> bool:
    """Reject a known oversized body before consuming the request stream."""

    if content_length is None:
        return False
    try:
        return int(content_length) > settings.webhook_max_payload_bytes
    except ValueError:
        return False


async def _read_bounded_body(request: Request, max_payload_bytes: int) -> bytes | None:
    """Read exactly one body up to a strict upper bound without logging its content."""

    chunks: list[bytes] = []
    received_bytes = 0
    async for chunk in request.stream():
        received_bytes += len(chunk)
        if received_bytes > max_payload_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)
