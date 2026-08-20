"""Identity phone normalization tests."""

import pytest

from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode
from app.modules.identity.domain.phone import mask_phone, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("90 123 45 67", "+998901234567"),
        ("998 (90) 123-45-67", "+998901234567"),
        ("+1 415 555 2671", "+14155552671"),
        ("0044 20 7946 0958", "+442079460958"),
    ],
)
def test_normalize_phone_returns_e164(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


def test_normalize_phone_rejects_ambiguous_input() -> None:
    with pytest.raises(IdentityDomainError) as captured:
        normalize_phone("123")

    assert captured.value.code is IdentityErrorCode.INVALID_REQUEST


def test_mask_phone_never_returns_full_value() -> None:
    phone = "+998901234567"

    masked = mask_phone(phone)

    assert masked != phone
    assert masked.endswith("67")
