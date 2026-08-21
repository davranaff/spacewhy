"""Compact Telegram start payloads for phone authentication challenges."""

from __future__ import annotations

from uuid import UUID

_PREFIX = "login_"


def build_phone_challenge_start_parameter(challenge_id: UUID) -> str:
    """Encode one challenge in Telegram's bounded start parameter alphabet."""

    return f"{_PREFIX}{challenge_id.hex}"


def parse_phone_challenge_start_parameter(message_text: str | None) -> UUID | None:
    """Read only the exact `/start login_<uuid>` command shape."""

    if message_text is None:
        return None
    parts = message_text.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].split("@", maxsplit=1)[0] != "/start":
        return None
    payload = parts[1].strip()
    if not payload.startswith(_PREFIX):
        return None
    encoded = payload.removeprefix(_PREFIX)
    if len(encoded) != 32:
        return None
    try:
        return UUID(hex=encoded)
    except ValueError:
        return None
