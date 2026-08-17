"""Safe, framework-independent localization errors."""


class I18nError(Exception):
    """Base error for catalog and localization failures."""


class CatalogValidationError(I18nError):
    """Translation catalogs cannot be used safely."""


class MissingTranslationError(I18nError):
    """A scoped localizer could not resolve a message key."""


class InterpolationError(I18nError):
    """A catalog template has missing or invalid parameters."""
