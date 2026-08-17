"""Strict gettext catalog and interpolation validation helpers."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable

from app.core.i18n.errors import CatalogValidationError, InterpolationError

_PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def placeholders(template: str) -> frozenset[str]:
    """Extract only simple named placeholders and reject formatting expressions."""

    matches = list(_PLACEHOLDER_PATTERN.finditer(template))
    cursor = 0
    names: set[str] = set()
    for match in matches:
        skipped = template[cursor : match.start()]
        if "{" in skipped or "}" in skipped:
            raise CatalogValidationError("Translation template contains an invalid placeholder.")
        names.add(match.group(1))
        cursor = match.end()
    if "{" in template[cursor:] or "}" in template[cursor:]:
        raise CatalogValidationError("Translation template contains an invalid placeholder.")
    return frozenset(names)


def interpolate(template: str, params: dict[str, object]) -> str:
    """Render validated simple placeholders without attribute or expression evaluation."""

    expected = placeholders(template)
    missing = expected - params.keys()
    if missing:
        rendered = ", ".join(sorted(missing))
        raise InterpolationError(f"Translation parameters are missing: {rendered}.")
    return _PLACEHOLDER_PATTERN.sub(lambda match: str(params[match.group(1)]), template)


def validate_placeholder_parity(template_groups: Iterable[tuple[str, tuple[str, ...]]]) -> None:
    """Require the same named parameters for a message across locale catalogs."""

    expected_by_key: dict[str, frozenset[str]] = {}
    for key, templates in template_groups:
        for template in templates:
            found = placeholders(template)
            expected = expected_by_key.setdefault(key, found)
            if found != expected:
                raise CatalogValidationError(
                    f"Translation placeholder mismatch for semantic key '{key}'."
                )


def duplicate_message_ids(po_text: str) -> set[str]:
    """Detect duplicate msgid declarations before Babel condenses a PO catalog."""

    seen: set[str] = set()
    duplicates: set[str] = set()
    lines = po_text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("msgid "):
            index += 1
            continue
        literal = line.removeprefix("msgid ").strip()
        value = _parse_po_literal(literal)
        index += 1
        while index < len(lines) and lines[index].lstrip().startswith('"'):
            value += _parse_po_literal(lines[index].strip())
            index += 1
        if value and value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _parse_po_literal(value: str) -> str:
    """Parse one PO quoted fragment without evaluating arbitrary code."""

    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError) as error:
        raise CatalogValidationError(
            "Translation catalog contains an invalid PO string."
        ) from error
    if not isinstance(parsed, str):
        raise CatalogValidationError("Translation catalog contains an invalid PO string.")
    return parsed
