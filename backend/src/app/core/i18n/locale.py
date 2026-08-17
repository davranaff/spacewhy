"""Validated, normalized BCP 47 locale tags."""

from __future__ import annotations

from babel import Locale as BabelLocale
from pydantic_core import core_schema


class Locale(str):
    """A normalized product locale that is safe for settings, paths, and logs."""

    _MAX_LENGTH = 35

    def __new__(cls, value: str) -> Locale:
        """Normalize a locale without silently accepting malformed input."""

        normalized_input = value.strip()
        if (
            not normalized_input
            or len(normalized_input) > cls._MAX_LENGTH
            or any(ord(character) < 32 for character in normalized_input)
        ):
            raise ValueError("Locale must be a short, non-empty BCP 47 tag.")
        normalized_bcp47 = normalized_input.replace("_", "-")
        try:
            parsed = BabelLocale.parse(normalized_bcp47, sep="-")
        except (ValueError, TypeError) as error:
            raise ValueError("Locale must be a valid BCP 47 tag.") from error
        language = parsed.language.lower()
        parts = normalized_bcp47.split("-")
        explicit_script = next(
            (part for part in parts[1:] if len(part) == 4 and part.isalpha()),
            None,
        )
        script = parsed.script if explicit_script is not None else None
        normalized = f"{language}-{script.title()}" if language == "uz" and script else language
        return str.__new__(cls, normalized)

    @classmethod
    def parse(cls, value: str | Locale) -> Locale:
        """Return a normalized locale value."""

        return value if isinstance(value, cls) else cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: object,
        _handler: object,
    ) -> core_schema.CoreSchema:
        """Allow Pydantic settings to validate locale fields and mapping values."""

        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
