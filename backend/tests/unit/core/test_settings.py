"""Configuration validation and secret-safety unit tests."""

import pytest
from pydantic import SecretStr
from pydantic import ValidationError as PydanticValidationError

from app.core.config.environment import Environment
from app.core.config.settings import (
    AppSettings,
    DatabaseSettings,
    LoggingSettings,
    SecuritySettings,
    Settings,
)


def test_production_rejects_debug_mode() -> None:
    """Production must never silently enable debug error behavior."""

    with pytest.raises(PydanticValidationError, match="APP__DEBUG"):
        Settings(
            app=AppSettings(environment=Environment.PRODUCTION, debug=True),
            logging=LoggingSettings(json_logs=True),
        )


def test_production_requires_json_logs() -> None:
    """Container production logging must be structured."""

    with pytest.raises(PydanticValidationError, match="LOGGING__JSON_LOGS"):
        Settings(app=AppSettings(environment=Environment.PRODUCTION))


def test_production_requires_an_explicit_database_url() -> None:
    """Production cannot accidentally use the checked-in local connection default."""

    with pytest.raises(PydanticValidationError, match="DATABASE__URL"):
        Settings(
            app=AppSettings(environment=Environment.PRODUCTION),
            database=DatabaseSettings(),
            logging=LoggingSettings(json_logs=True),
        )


def test_cors_credentials_rejects_wildcards() -> None:
    """Wildcard CORS origins cannot be combined with credentialed requests."""

    with pytest.raises(PydanticValidationError, match="CORS wildcards"):
        Settings(
            security=SecuritySettings(
                cors_allowed_origins=("*",),
                cors_allow_credentials=True,
            )
        )


def test_database_url_is_secret_in_settings_repr() -> None:
    """Configuration repr must not reveal a connection password."""

    database = DatabaseSettings(
        url=SecretStr("postgresql+asyncpg://user:super-secret@localhost:5432/spacewhy")
    )

    assert "super-secret" not in repr(database)
    assert "**********" in repr(database)


def test_database_requires_async_postgresql_driver() -> None:
    """Sync or non-PostgreSQL URLs fail during configuration construction."""

    with pytest.raises(PydanticValidationError, match="postgresql\\+asyncpg"):
        DatabaseSettings(url=SecretStr("postgresql://user:password@localhost:5432/spacewhy"))
