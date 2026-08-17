"""Clock contract for deterministic application behavior."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provide timezone-aware current time."""

    def now(self) -> datetime:
        """Return the current UTC-aware timestamp."""

        ...
