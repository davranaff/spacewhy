"""Small platform endpoints; domain URLs will be mounted after ownership is defined."""

import logging

from asgiref.sync import sync_to_async
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.urls import path

logger = logging.getLogger(__name__)


@sync_to_async(thread_sensitive=True)
def _ensure_database_connection() -> None:
    """Bridge the synchronous Django connection check at this platform boundary only."""

    connection.ensure_connection()


async def live(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


async def ready(_request: HttpRequest) -> JsonResponse:
    try:
        await _ensure_database_connection()
    except Exception:  # noqa: BLE001 - readiness must report dependency failure as 503.
        logger.exception("database readiness check failed")
        return JsonResponse({"status": "not_ready"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/live", live, name="health-live"),
    path("health/ready", ready, name="health-ready"),
]
