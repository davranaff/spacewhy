"""Validated configuration loaded once at the composition root."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.bots.settings import BotsSettings
from app.core.config.environment import Environment
from app.core.constants import API_V1_PREFIX
from app.core.i18n.settings import I18nSettings

_DEFAULT_LOCAL_DATABASE_URL = (
    "postgresql+asyncpg://spacewhy:spacewhy_local_password@127.0.0.1:5432/spacewhy"
)
_DEFAULT_LOCAL_SESSION_SIGNING_SECRET = (
    "local-development-session-signing-secret-change-before-production"
)


class AppSettings(BaseModel):
    """Application identity and lifecycle behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(default="spacewhy", min_length=1, max_length=100)
    version: str = Field(default="0.1.0", min_length=1, max_length=50)
    environment: Environment = Environment.LOCAL
    debug: bool = False
    verify_dependencies_on_startup: bool = False


class APISettings(BaseModel):
    """Public HTTP and OpenAPI settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(default="Spacewhy API", min_length=1, max_length=120)
    description: str = "Spacewhy platform API."
    prefix: str = API_V1_PREFIX
    docs_enabled: bool = True
    openapi_enabled: bool = True

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        """Keep the global versioned router path predictable."""

        normalized = value.rstrip("/")
        if not normalized or not normalized.startswith("/"):
            message = "API prefix must be a non-root path beginning with '/'."
            raise ValueError(message)
        return normalized


class DatabaseSettings(BaseModel):
    """Async PostgreSQL connectivity and pool limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: SecretStr = SecretStr(_DEFAULT_LOCAL_DATABASE_URL)
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=5, ge=0, le=100)
    pool_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    pool_recycle_seconds: int = Field(default=1800, ge=0)
    command_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    health_timeout_seconds: float = Field(default=2.0, gt=0, le=30)

    @field_validator("url")
    @classmethod
    def validate_async_postgres_url(cls, value: SecretStr) -> SecretStr:
        """Reject accidental sync drivers and non-PostgreSQL URLs at startup."""

        url = value.get_secret_value()
        if not url.startswith("postgresql+asyncpg://"):
            message = "DATABASE__URL must use the postgresql+asyncpg:// scheme."
            raise ValueError(message)
        if "@" not in url or url.rsplit("/", maxsplit=1)[-1] == "":
            message = "DATABASE__URL must include a host and database name."
            raise ValueError(message)
        return value

    @property
    def resolved_url(self) -> str:
        """Return the driver URL only where a database adapter needs it."""

        return self.url.get_secret_value()


class LoggingSettings(BaseModel):
    """Container-friendly logging behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    json_logs: bool = False


class ObservabilitySettings(BaseModel):
    """Vendor-neutral OpenTelemetry lifecycle settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    service_name: str = Field(default="spacewhy-backend", min_length=1, max_length=100)


class SecuritySettings(BaseModel):
    """Safe HTTP exposure and proxy boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trusted_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    cors_allowed_origins: tuple[str, ...] = ()
    cors_allowed_methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    cors_allowed_headers: tuple[str, ...] = ()
    cors_allow_credentials: bool = False
    proxy_headers_enabled: bool = False
    trusted_proxy_hosts: tuple[str, ...] = ()
    session_signing_secret: SecretStr = SecretStr(_DEFAULT_LOCAL_SESSION_SIGNING_SECRET)
    session_token_ttl_seconds: int = Field(default=3_600, ge=300, le=86_400)

    @property
    def resolved_session_signing_secret(self) -> str:
        """Expose session material only to composition roots that construct a signer."""

        return self.session_signing_secret.get_secret_value()

    @field_validator("session_signing_secret")
    @classmethod
    def validate_session_signing_secret(cls, value: SecretStr) -> SecretStr:
        """Keep signed-session entropy independent from the transport implementation."""

        if len(value.get_secret_value()) < 32:
            raise ValueError("Session signing secret must be at least 32 characters long.")
        return value


class Settings(BaseSettings):
    """The one typed source of runtime configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=(".env", "../deployment/env/.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = AppSettings()
    api: APISettings = APISettings()
    database: DatabaseSettings = DatabaseSettings()
    logging: LoggingSettings = LoggingSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    security: SecuritySettings = SecuritySettings()
    i18n: I18nSettings = I18nSettings()
    bots: BotsSettings = BotsSettings()

    @model_validator(mode="after")
    def validate_security_invariants(self) -> Settings:
        """Fail fast for configurations that weaken production protections."""

        wildcard_origins = "*" in self.security.cors_allowed_origins
        wildcard_methods = "*" in self.security.cors_allowed_methods
        wildcard_headers = "*" in self.security.cors_allowed_headers
        if self.security.cors_allow_credentials and (
            wildcard_origins or wildcard_methods or wildcard_headers
        ):
            message = "CORS wildcards cannot be combined with credentials."
            raise ValueError(message)
        if self.security.proxy_headers_enabled and not self.security.trusted_proxy_hosts:
            message = "Trusted proxy hosts are required when proxy headers are enabled."
            raise ValueError(message)
        if self.app.environment.is_production:
            if self.app.debug:
                raise ValueError("APP__DEBUG must be false in production.")
            if not self.logging.json_logs:
                raise ValueError("LOGGING__JSON_LOGS must be true in production.")
            if self.database.resolved_url == _DEFAULT_LOCAL_DATABASE_URL:
                raise ValueError("DATABASE__URL must be explicitly configured in production.")
            if (
                self.security.resolved_session_signing_secret
                == _DEFAULT_LOCAL_SESSION_SIGNING_SECRET
            ):
                raise ValueError(
                    "SECURITY__SESSION_SIGNING_SECRET must be explicitly configured in production."
                )
            if "*" in self.security.trusted_hosts:
                raise ValueError("SECURITY__TRUSTED_HOSTS cannot contain '*' in production.")
        for app_id, bot_settings in self.bots.apps.items():
            unsupported_locales = bot_settings.supported_locales - self.i18n.supported_locales
            if unsupported_locales:
                rendered_locales = ", ".join(sorted(map(str, unsupported_locales)))
                raise ValueError(
                    f"Bot app '{app_id}' has locales outside I18N__SUPPORTED_LOCALES: "
                    f"{rendered_locales}."
                )
        return self
