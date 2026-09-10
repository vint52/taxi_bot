"""Rendering of balance, rides and service texts for Telegram (HTML parse mode)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from constants import (
    BALANCE_TEMPLATE,
    LAST_UPDATE_TEMPLATE,
    MSG_TRUNCATED,
    NO_TRIPS_TEMPLATE,
    TELEGRAM_MESSAGE_LIMIT,
    TRIP_TEMPLATE,
)
from models import Trip


def format_decimal(value: float, decimals: int = 2) -> str:
    """Format a number without trailing zeros: 12.50 -> "12.5", 3.0 -> "3"."""
    text = f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    return text or "0"


def format_price(value: float) -> str:
    """Format money as an integer when it has no fractional part."""
    number = float(value)
    return str(int(number)) if number.is_integer() else format_decimal(number)


def format_trip(trip: Trip, index: int) -> str:
    """Render one ride as an HTML blockquote."""
    return TRIP_TEMPLATE.format(
        index=index,
        time=datetime.fromtimestamp(trip.time).strftime("%d.%m.%Y %H:%M"),
        name=escape(trip.name),
        phone=escape(trip.phone),
        from_address=escape(trip.from_address),
        to_address=escape(trip.to_address),
        distance=format_decimal(trip.distance),
        waiting=format_decimal(trip.waiting, decimals=1),
        price=format_price(trip.price),
    )


def format_balance_message(balance: int | None, trips: list[Trip]) -> str:
    """Render the balance header followed by rides, newest first."""
    if trips:
        rendered = "\n\n".join(
            format_trip(trip, index) for index, trip in enumerate(reversed(trips), start=1)
        )
    else:
        rendered = NO_TRIPS_TEMPLATE
    return BALANCE_TEMPLATE.format(balance=format_price(balance or 0), trips=rendered)


def format_last_update(timestamp: int, tz: ZoneInfo) -> str:
    """Render the "last update" footer shown to the administrator."""
    moment = datetime.fromtimestamp(timestamp, tz).strftime("%d.%m.%Y %H:%M")
    return LAST_UPDATE_TEMPLATE.format(time=moment)


def truncate(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    """Cut ``text`` so that it fits into a single Telegram message."""
    if len(text) <= limit:
        return text
    return text[: limit - len(MSG_TRUNCATED)] + MSG_TRUNCATED
