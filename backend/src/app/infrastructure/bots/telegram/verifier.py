"""Constant-time Telegram webhook and signed WebApp initData verification."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest, new
from typing import cast
from urllib.parse import parse_qsl

from pydantic import SecretStr

from app.core.bots.contracts import TelegramWebAppIdentity
from app.core.bots.settings import BotAppSettings


def verify_telegram_webhook_secret(
    configured_secret: SecretStr | None,
    presented_secret: str | None,
) -> bool:
    """Compare the exact configured secret without revealing its value or presence."""

    if configured_secret is None or presented_secret is None:
        return False
    return compare_digest(configured_secret.get_secret_value(), presented_secret)


class TelegramWebAppVerifier:
    """Validate initData with the token of exactly one configured Telegram bot."""

    def __init__(self, settings: BotAppSettings) -> None:
        """Resolve a token only in the approved credential-verification boundary."""

        if settings.token is None:
            raise ValueError("Telegram WebApp verification requires an enabled bot token.")
        self._token_bytes = settings.token.get_secret_value().encode("utf-8")

    def verify_init_data(
        self,
        init_data: str,
        *,
        max_age_seconds: int,
        now: datetime,
    ) -> TelegramWebAppIdentity:
        """Check Telegram's official HMAC, age, and safely shaped user fields."""

        if not init_data or max_age_seconds <= 0:
            raise ValueError("Telegram initData is invalid.")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Verification time must be timezone-aware.")
        values = self._parse_values(init_data)
        presented_hash = values.pop("hash", None)
        auth_date_text = values.get("auth_date")
        user_json = values.get("user")
        if (
            not isinstance(presented_hash, str)
            or not isinstance(auth_date_text, str)
            or not isinstance(user_json, str)
        ):
            raise ValueError("Telegram initData is missing required fields.")
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(values.items(), key=lambda item: item[0])
        )
        secret_key = new(b"WebAppData", self._token_bytes, sha256).digest()
        calculated_hash = new(secret_key, data_check_string.encode("utf-8"), sha256).hexdigest()
        if not compare_digest(calculated_hash, presented_hash):
            raise ValueError("Telegram initData signature is invalid.")
        try:
            auth_date = datetime.fromtimestamp(int(auth_date_text), tz=UTC)
        except (OverflowError, ValueError) as error:
            raise ValueError("Telegram initData auth_date is invalid.") from error
        now_utc = now.astimezone(UTC)
        if auth_date > now_utc + timedelta(seconds=60):
            raise ValueError("Telegram initData auth_date is in the future.")
        if now_utc - auth_date > timedelta(seconds=max_age_seconds):
            raise ValueError("Telegram initData has expired.")
        return self._parse_identity(user_json, auth_date)

    @staticmethod
    def _parse_values(init_data: str) -> dict[str, str]:
        """Reject duplicate or malformed query fields before signature calculation."""

        parsed = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        values: dict[str, str] = {}
        for key, value in parsed:
            if not key or key in values:
                raise ValueError("Telegram initData has duplicate or empty fields.")
            values[key] = value
        return values

    @staticmethod
    def _parse_identity(user_json: str, auth_date: datetime) -> TelegramWebAppIdentity:
        """Decode only the provider profile fields allowed into a signed session."""

        try:
            parsed_user: object = json.loads(user_json)
        except json.JSONDecodeError as error:
            raise ValueError("Telegram initData user is invalid.") from error
        if not isinstance(parsed_user, dict):
            raise ValueError("Telegram initData user is invalid.")
        raw_user = cast(dict[str, object], parsed_user)
        raw_id = raw_user.get("id")
        first_name = raw_user.get("first_name")
        last_name = _optional_text(raw_user.get("last_name"))
        username = _optional_text(raw_user.get("username"))
        language_code = _optional_text(raw_user.get("language_code"))
        if not isinstance(raw_id, int) or raw_id <= 0 or not isinstance(first_name, str):
            raise ValueError("Telegram initData user is invalid.")
        return TelegramWebAppIdentity(
            user_id=str(raw_id),
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            auth_date=auth_date,
        )


def _optional_text(value: object) -> str | None:
    """Allow a nullable Telegram profile field and reject every other value."""

    if value is None or isinstance(value, str):
        return value
    raise ValueError("Telegram initData user is invalid.")
