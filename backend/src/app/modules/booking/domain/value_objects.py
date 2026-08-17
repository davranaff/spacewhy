"""Pure time, money, and interval value objects used by booking use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

_MONEY_QUANTUM = Decimal("0.01")


def require_aware(value: datetime, *, field_name: str) -> datetime:
    """Normalize an aware timestamp to UTC and reject naive persistence inputs."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, order=True)
class TimeRange:
    """A non-empty half-open UTC interval."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", require_aware(self.start, field_name="start"))
        object.__setattr__(self, "end", require_aware(self.end, field_name="end"))
        if self.end <= self.start:
            raise ValueError("TimeRange end must be after start.")

    @property
    def duration(self) -> timedelta:
        """Return exact interval duration."""

        return self.end - self.start

    def overlaps(self, other: TimeRange) -> bool:
        """Apply half-open interval overlap semantics."""

        return self.start < other.end and other.start < self.end

    def contains(self, other: TimeRange) -> bool:
        """Return whether another interval fits entirely inside this interval."""

        return self.start <= other.start and other.end <= self.end


@dataclass(frozen=True, slots=True)
class Money:
    """Exact money in the configured ISO currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if len(self.currency) != 3 or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError("Currency must be a three-letter uppercase ISO code.")
        quantized = self.amount.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if quantized < Decimal("0"):
            raise ValueError("Money amount cannot be negative.")
        object.__setattr__(self, "amount", quantized)

    def add(self, other: Money) -> Money:
        """Add same-currency values exactly."""

        if self.currency != other.currency:
            raise ValueError("Money currencies must match.")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: Money) -> Money:
        """Subtract same-currency values without permitting a negative result."""

        if self.currency != other.currency:
            raise ValueError("Money currencies must match.")
        return Money(amount=self.amount - other.amount, currency=self.currency)
