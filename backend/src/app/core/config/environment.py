"""Supported runtime environments."""

from enum import StrEnum


class Environment(StrEnum):
    """Explicit runtime environments with production-safe validation."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        """Return whether this environment must use production safeguards."""

        return self is self.PRODUCTION
