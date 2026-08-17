"""Request ID safety unit tests."""

from app.core.http.middleware.request_id import is_valid_request_id


def test_request_id_accepts_canonical_uuid() -> None:
    """Canonical UUID text is accepted and remains safe for log fields."""

    assert is_valid_request_id("02cd8ed7-a998-41fc-8d8d-c59ea9987f18")


def test_request_id_rejects_log_injection_and_noncanonical_values() -> None:
    """Malformed or excessive incoming values are never forwarded to logs."""

    assert not is_valid_request_id("not-a-uuid\nINFO forged")
    assert not is_valid_request_id("02CD8ED7-A998-41FC-8D8D-C59EA9987F18")
    assert not is_valid_request_id("a" * 65)
