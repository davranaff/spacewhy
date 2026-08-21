"""Strict transport schemas for shared Identity endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.public import IdentityPrincipal, IdentitySession


class _Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PhoneChallengeRequest(_Schema):
    phone: str = Field(min_length=8, max_length=32)


class PhoneChallengeResponse(_Schema):
    challenge_id: UUID
    expires_at: datetime
    telegram_start_parameter: str = Field(pattern=r"^login_[0-9a-f]{32}$")
    status: Literal["accepted"] = "accepted"


class VerifyChallengeRequest(_Schema):
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class TelegramWebAppRequest(_Schema):
    init_data: str = Field(min_length=1, max_length=16_384)


class CreateHandoffRequest(_Schema):
    target: Literal["finance"]


class HandoffResponse(_Schema):
    handoff_token: str
    expires_at: datetime


class ExchangeHandoffRequest(_Schema):
    target: Literal["finance"]
    handoff_token: str = Field(min_length=32, max_length=128)


class PrincipalResponse(_Schema):
    id: UUID
    display_name: str | None
    locale: str

    @classmethod
    def from_principal(cls, value: IdentityPrincipal) -> PrincipalResponse:
        return cls(id=value.id, display_name=value.display_name, locale=value.locale)


class SessionResponse(_Schema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    principal: PrincipalResponse

    @classmethod
    def from_session(cls, value: IdentitySession) -> SessionResponse:
        return cls(
            access_token=value.access_token,
            expires_at=value.expires_at,
            principal=PrincipalResponse.from_principal(value.principal),
        )
