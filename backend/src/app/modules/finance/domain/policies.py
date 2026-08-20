"""Pure ledger invariants shared by application commands."""

from decimal import Decimal

from app.modules.finance.domain.enums import EntryDirection
from app.modules.finance.domain.errors import FinanceDomainError, FinanceErrorCode


def validate_currency(value: str) -> str:
    normalized = value.upper()
    if len(normalized) != 3 or not normalized.isalpha() or not normalized.isascii():
        raise FinanceDomainError(FinanceErrorCode.INVALID_REQUEST)
    return normalized


def validate_amount(value: Decimal) -> Decimal:
    if not value.is_finite() or value <= 0 or value.quantize(Decimal("0.01")) != value:
        raise FinanceDomainError(FinanceErrorCode.INVALID_REQUEST)
    return value


def balance_delta(direction: EntryDirection, amount: Decimal) -> Decimal:
    validate_amount(amount)
    return amount if direction is EntryDirection.INCOME else -amount
