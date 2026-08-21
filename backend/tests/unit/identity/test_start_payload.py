"""Telegram deep-link payload boundaries for phone authentication."""

from uuid import UUID, uuid4

from app.modules.identity.domain.start_payload import (
    build_phone_challenge_start_parameter,
    parse_phone_challenge_start_parameter,
)


def test_phone_challenge_start_parameter_round_trip() -> None:
    challenge_id = uuid4()
    parameter = build_phone_challenge_start_parameter(challenge_id)

    assert parameter == f"login_{challenge_id.hex}"
    assert len(parameter) <= 64
    assert parse_phone_challenge_start_parameter(f"/start {parameter}") == challenge_id
    assert (
        parse_phone_challenge_start_parameter(f"/start@Auth_Spacewhy_bot {parameter}")
        == challenge_id
    )


def test_phone_challenge_start_parameter_rejects_other_commands() -> None:
    challenge_id = UUID("00112233-4455-6677-8899-aabbccddeeff")

    assert parse_phone_challenge_start_parameter(None) is None
    assert parse_phone_challenge_start_parameter("/start") is None
    assert parse_phone_challenge_start_parameter(f"/help login_{challenge_id.hex}") is None
    assert parse_phone_challenge_start_parameter("/start login_bad") is None
