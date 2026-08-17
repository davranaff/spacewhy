"""Structured logging redaction tests."""

import logging

import pytest

from app.core.config.settings import ObservabilitySettings, Settings
from app.core.observability.logging import JsonFormatter
from app.core.observability.redaction import redact, redact_text
from app.core.observability.telemetry import Telemetry, current_trace_id


def test_redaction_masks_sensitive_values_recursively() -> None:
    """Nested logging payloads retain shape but not credentials."""

    payload = {
        "token": "top-secret",
        "bot_token": "telegram-secret",
        "webhook_secret": "webhook-secret",
        "nested": {
            "database_url": "postgresql+asyncpg://user:password@localhost/database",
            "safe": "visible",
        },
    }

    assert redact(payload) == {
        "token": "[REDACTED]",
        "bot_token": "[REDACTED]",
        "webhook_secret": "[REDACTED]",
        "nested": {
            "database_url": "[REDACTED]",
            "safe": "visible",
        },
    }


def test_text_redaction_masks_database_urls_and_assignments() -> None:
    """Exception rendering does not expose credential-shaped text."""

    rendered = redact_text(
        "database_url=postgresql+asyncpg://user:password@localhost/database "
        "token=top-secret webhook_secret=webhook-secret"
    )

    assert "password" not in rendered
    assert "top-secret" not in rendered
    assert "webhook-secret" not in rendered
    assert "[REDACTED]" in rendered


@pytest.mark.asyncio
async def test_enabled_telemetry_provides_trace_context_without_collector() -> None:
    """Telemetry creates local span context and shuts down without external infrastructure."""

    telemetry = Telemetry(Settings(observability=ObservabilitySettings(enabled=True)))
    telemetry.initialize()

    with telemetry.start_server_span(method="GET", request_id="test-request") as span:
        assert span is not None
        assert current_trace_id() is not None

    await telemetry.shutdown()


def test_structured_bot_log_never_serializes_credentials() -> None:
    """Bot-specific sensitive key names are redacted in JSON logging too."""

    record = logging.makeLogRecord(
        {
            "name": "spacewhy",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "webhook_secret=webhook-secret",
            "bot_token": "telegram-secret",
            "bot_app_id": "support_bot",
            "owner_module": "support",
            "provider": "telegram",
        }
    )

    rendered = JsonFormatter().format(record)

    assert "webhook-secret" not in rendered
    assert "telegram-secret" not in rendered
    assert '"bot_app_id": "support_bot"' in rendered
