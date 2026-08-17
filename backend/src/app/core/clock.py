"""Production implementation of the clock contract."""

from datetime import UTC, datetime


class SystemClock:
    """Return current UTC-aware timestamps."""

    def now(self) -> datetime:
        """Return the current time in UTC."""

        return datetime.now(UTC)
