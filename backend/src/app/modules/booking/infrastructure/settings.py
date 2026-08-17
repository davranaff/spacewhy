"""Booking-specific runtime tuning loaded independently from core infrastructure defaults."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BookingModuleSettings(BaseSettings):
    """Safe module configuration with explicit environment names and bounded values."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=(".env", "../deployment/env/.env"),
        env_file_encoding="utf-8",
        env_prefix="BOOKING_",
        extra="ignore",
    )

    webapp_max_age_seconds: int = Field(default=600, ge=60, le=3_600)
    auth_rate_limit_requests: int = Field(default=20, ge=1, le=200)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    availability_max_days: int = Field(default=31, ge=1, le=90)
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    worker_batch_size: int = Field(default=50, ge=1, le=500)
    worker_lease_seconds: int = Field(default=300, ge=30, le=3_600)
    callback_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
