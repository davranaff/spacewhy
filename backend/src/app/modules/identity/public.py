"""The only cross-module Identity contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IdentityPrincipal:
    """Verified active principal exposed without phone or Telegram identifiers."""

    id: UUID
    display_name: str | None
    locale: str


@dataclass(frozen=True, slots=True)
class IdentitySession:
    """Short-lived bearer session returned after verified authentication."""

    access_token: str
    expires_at: datetime
    principal: IdentityPrincipal


class IdentityAccess(Protocol):
    """Narrow authentication capability used by other presentation boundaries."""

    async def principal_from_session_token(self, token: str) -> IdentityPrincipal:
        """Verify a token and reload the current active principal."""

        ...
