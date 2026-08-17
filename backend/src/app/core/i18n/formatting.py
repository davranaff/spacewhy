"""Locale-aware formatting helpers built on Babel."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from babel.dates import format_date as babel_format_date
from babel.dates import format_datetime as babel_format_datetime
from babel.dates import format_time as babel_format_time
from babel.numbers import format_currency as babel_format_currency
from babel.numbers import format_decimal as babel_format_decimal
from babel.numbers import format_percent as babel_format_percent

from app.core.i18n.locale import Locale


def format_number(value: Decimal | float | int, *, locale: Locale) -> str:
    """Format a number using the requested locale."""

    return babel_format_decimal(value, locale=str(locale))


def format_currency(value: Decimal | float | int, currency: str, *, locale: Locale) -> str:
    """Format an ISO currency amount using the requested locale."""

    return babel_format_currency(value, currency, locale=str(locale))


def format_percentage(value: Decimal | float | int, *, locale: Locale) -> str:
    """Format a ratio as a localized percentage."""

    return babel_format_percent(value, locale=str(locale))


def format_local_date(value: date, *, locale: Locale) -> str:
    """Format a calendar date without introducing a timezone."""

    return babel_format_date(value, locale=str(locale))


def format_local_time(value: time, *, locale: Locale) -> str:
    """Format a time using the requested locale."""

    return babel_format_time(value, locale=str(locale))


def format_local_datetime(value: datetime, *, locale: Locale) -> str:
    """Format only timezone-aware datetimes."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime formatting requires a timezone-aware value.")
    return babel_format_datetime(value, locale=str(locale))
