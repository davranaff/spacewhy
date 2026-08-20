"""Finance money and currency invariant tests."""

from decimal import Decimal

import pytest

from app.modules.finance.domain.enums import EntryDirection
from app.modules.finance.domain.errors import FinanceDomainError, FinanceErrorCode
from app.modules.finance.domain.policies import balance_delta, validate_amount, validate_currency


def test_currency_and_balance_direction_are_explicit() -> None:
    assert validate_currency("uzs") == "UZS"
    assert balance_delta(EntryDirection.INCOME, Decimal("10.50")) == Decimal("10.50")
    assert balance_delta(EntryDirection.EXPENSE, Decimal("10.50")) == Decimal("-10.50")


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1"), Decimal("1.001")])
def test_amount_rejects_non_positive_or_fractional_minor_units(value: Decimal) -> None:
    with pytest.raises(FinanceDomainError) as captured:
        validate_amount(value)

    assert captured.value.code is FinanceErrorCode.INVALID_REQUEST


def test_currency_rejects_non_iso_shape() -> None:
    with pytest.raises(FinanceDomainError):
        validate_currency("USDT")
