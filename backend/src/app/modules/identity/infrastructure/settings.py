"""Identity-specific safe runtime tuning."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentityModuleSettings(BaseSettings):
    """Bounded configuration loaded at the composition root."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=(".env", "../deployment/env/.env"),
        env_file_encoding="utf-8",
        env_prefix="IDENTITY_",
        extra="ignore",
    )

    bot_app_id: str = Field(default="spacewhy_auth_bot", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    otp_ttl_seconds: int = Field(default=300, ge=60, le=900)
    otp_attempts: int = Field(default=5, ge=1, le=10)
    access_token_ttl_seconds: int = Field(default=900, ge=300, le=3_600)
    handoff_ttl_seconds: int = Field(default=60, ge=30, le=300)
    webapp_max_age_seconds: int = Field(default=600, ge=60, le=3_600)
