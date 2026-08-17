"""Validate configuration before the ASGI process starts without connecting to PostgreSQL."""

from app.core.config.settings import Settings


def main() -> None:
    """Load typed settings once and print only non-sensitive startup metadata."""

    settings = Settings()
    print(
        "Configuration validated "
        f"for environment={settings.app.environment.value} "
        f"service={settings.observability.service_name}"
    )


if __name__ == "__main__":
    main()
