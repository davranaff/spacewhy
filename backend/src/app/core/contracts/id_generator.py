"""Identifier-generation contract for explicit dependency injection."""

from typing import Protocol
from uuid import UUID


class IdGenerator(Protocol):
    """Generate opaque UUID identifiers."""

    def new(self) -> UUID:
        """Return a newly generated UUID."""

        ...
