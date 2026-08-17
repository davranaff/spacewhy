"""Recursive redaction for structured logs and exception text."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set_cookie",
        "api_key",
        "client_secret",
        "database_url",
        "bot_token",
        "telegram_token",
        "webhook_secret",
        "provider_token",
    }
)
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(bot_token|telegram_token|webhook_secret|provider_token|access_token|refresh_token|client_secret|database_url|password|secret|token|authorization|cookie|api_key)\b([:=])([^\s,;]+)"
)
_POSTGRES_URL_PATTERN = re.compile(r"postgres(?:ql)?(?:\+[a-z0-9_]+)?://[^\s,;]+", re.IGNORECASE)


def is_sensitive_key(key: str) -> bool:
    """Return whether a key could contain a credential or authentication value."""

    normalized = key.lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or any(
        sensitive in normalized
        for sensitive in ("password", "secret", "token", "authorization", "cookie", "api_key")
    )


def redact_text(value: str) -> str:
    """Mask common sensitive text patterns without logging credential-like values."""

    without_database_url = _POSTGRES_URL_PATTERN.sub("[REDACTED]", value)
    return _ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        without_database_url,
    )


def redact(value: Any) -> Any:
    """Recursively redact known sensitive keys while preserving useful structure."""

    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {
            str(key): "[REDACTED]" if is_sensitive_key(str(key)) else redact(item)
            for key, item in mapping.items()
        }
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        sequence = cast(Sequence[object], value)
        return [redact(item) for item in sequence]
    return value
