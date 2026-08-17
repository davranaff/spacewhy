"""Production implementation of identifier generation."""

from uuid import UUID, uuid4


class UUID4Generator:
    """Generate random UUIDv4 values."""

    def new(self) -> UUID:
        """Return a new UUIDv4."""

        return uuid4()
