"""Single-owner structured logging configuration for container deployments."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config.settings import Settings
from app.core.http.context import get_request_context
from app.core.observability.redaction import is_sensitive_key, redact, redact_text
from app.core.observability.telemetry import current_trace_id

_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


class ContextFilter(logging.Filter):
    """Attach stable service, environment, request, and trace metadata to each record."""

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._service = settings.observability.service_name
        self._environment = settings.app.environment.value

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich records without changing their message or propagating global state."""

        record.service = self._service
        record.environment = self._environment
        context = get_request_context()
        if context is not None and not hasattr(record, "request_id"):
            record.request_id = context.request_id
        if context is not None and context.locale is not None and not hasattr(record, "locale"):
            record.locale = str(context.locale)
        if not hasattr(record, "trace_id"):
            record.trace_id = current_trace_id()
        return True


class JsonFormatter(logging.Formatter):
    """Render safe JSON logs for production stdout collection."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize known metadata plus safe structured extras."""

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": redact_text(record.getMessage()),
            "service": getattr(record, "service", None),
            "environment": getattr(record, "environment", None),
            "request_id": getattr(record, "request_id", None),
            "trace_id": getattr(record, "trace_id", None),
            "route": getattr(record, "route", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "locale": getattr(record, "locale", None),
            "bot_app_id": getattr(record, "bot_app_id", None),
            "owner_module": getattr(record, "owner_module", None),
            "provider": getattr(record, "provider", None),
            "result": getattr(record, "result", None),
            "event": getattr(record, "event", None),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and key not in payload:
                payload[key] = "[REDACTED]" if is_sensitive_key(key) else redact(value)
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, sort_keys=True)


class HumanFormatter(logging.Formatter):
    """Render concise safe logs for local development."""

    def format(self, record: logging.LogRecord) -> str:
        """Keep local output readable while retaining correlation metadata."""

        timestamp = datetime.fromtimestamp(record.created, UTC).isoformat()
        request_id = getattr(record, "request_id", None)
        trace_id = getattr(record, "trace_id", None)
        route = getattr(record, "route", None)
        status_code = getattr(record, "status_code", None)
        duration_ms = getattr(record, "duration_ms", None)
        locale = getattr(record, "locale", None)
        bot_app_id = getattr(record, "bot_app_id", None)
        owner_module = getattr(record, "owner_module", None)
        provider = getattr(record, "provider", None)
        result = getattr(record, "result", None)
        message = redact_text(record.getMessage())
        rendered = (
            f"{timestamp} {record.levelname} {record.name} "
            f"request_id={request_id} trace_id={trace_id} route={route} "
            f"status_code={status_code} duration_ms={duration_ms} locale={locale} "
            f"bot_app_id={bot_app_id} owner_module={owner_module} provider={provider} "
            f"result={result} {message}"
        )
        if record.exc_info:
            return f"{rendered}\n{redact_text(self.formatException(record.exc_info))}"
        return rendered


def configure_logging(settings: Settings) -> None:
    """Configure only the application logger to avoid duplicate Uvicorn output."""

    application_logger = logging.getLogger("spacewhy")
    application_logger.handlers.clear()
    application_logger.setLevel(settings.logging.level)
    application_logger.propagate = False

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.addFilter(ContextFilter(settings))
    formatter: logging.Formatter
    formatter = JsonFormatter() if settings.logging.json_logs else HumanFormatter()
    handler.setFormatter(formatter)
    application_logger.addHandler(handler)
