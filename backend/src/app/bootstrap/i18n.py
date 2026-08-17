"""Composition-root construction for the core localization runtime."""

from app.core.config.settings import Settings
from app.core.i18n.localizer import LocalizationRuntime
from app.core.observability.telemetry import Telemetry


def create_localization_runtime(
    settings: Settings,
    telemetry: Telemetry,
) -> LocalizationRuntime:
    """Create a per-app catalog runtime without loading files during import."""

    return LocalizationRuntime(settings.i18n, settings.app.environment, metrics=telemetry)
