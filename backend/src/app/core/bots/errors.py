"""Safe errors for bot configuration, ownership, and webhook processing."""


class BotPlatformError(Exception):
    """Base error whose message must never include credentials."""


class BotConfigurationError(BotPlatformError):
    """Bot settings are incomplete or conflict with another bot app."""


class BotRegistrationError(BotPlatformError):
    """Module ownership declarations do not match configured bot apps."""


class BotRuntimeError(BotPlatformError):
    """An isolated bot runtime cannot safely process an update."""


class BotMalformedUpdateError(BotRuntimeError):
    """A provider payload cannot be mapped into the internal update contract."""


class BotUpdateTimeoutError(BotRuntimeError):
    """A bounded update processing window elapsed before completion."""


class BotProviderFailureError(BotRuntimeError):
    """A provider or handler failure has been sanitized for the delivery boundary."""


class WebhookVerificationError(BotPlatformError):
    """A webhook request failed an intentionally non-revealing validation step."""
