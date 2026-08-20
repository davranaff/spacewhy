"""Phone normalization rules owned by Identity."""

from __future__ import annotations

import re

from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode

_SEPARATORS = re.compile(r"[\s()\-.]")
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")


def normalize_phone(value: str) -> str:
    """Normalize common Uzbek input to E.164 and reject ambiguous values."""

    normalized = _SEPARATORS.sub("", value.strip())
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    elif normalized.startswith("998") and not normalized.startswith("+"):
        normalized = f"+{normalized}"
    elif normalized.isdigit() and len(normalized) == 9:
        normalized = f"+998{normalized}"
    if not _E164.fullmatch(normalized):
        raise IdentityDomainError(IdentityErrorCode.INVALID_REQUEST)
    return normalized


def mask_phone(value: str) -> str:
    """Return a display-safe phone hint without exposing the full identifier."""

    return f"{value[:4]}***{value[-2:]}"
