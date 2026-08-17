"""Public, non-secret bot application identifiers."""

from __future__ import annotations

import re

from pydantic_core import core_schema

_BOT_APP_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class BotAppId(str):
    """A stable safe identifier used in settings, webhook routes, and logs."""

    def __new__(cls, value: str) -> BotAppId:
        """Validate an identifier without accepting path-like or Unicode variants."""

        if not _BOT_APP_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "Bot app ID must use lowercase ASCII letters, digits, and underscores."
            )
        return str.__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: object,
        _handler: object,
    ) -> core_schema.CoreSchema:
        """Allow strongly typed mapping keys in Pydantic settings."""

        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
