from datetime import datetime
from zoneinfo import ZoneInfo

from conftest import make_trip
from constants import MSG_TRUNCATED, NO_TRIPS_TEMPLATE
from formatting import (
    format_balance_message,
    format_decimal,
    format_last_update,
    format_price,
    format_trip,
    truncate,
)


def test_format_decimal():
    assert format_decimal(12.50) == "12.5"
    assert format_decimal(3.0) == "3"
    assert format_decimal(0) == "0"
    assert format_decimal(2.25, decimals=1) == "2.2"


def test_format_price():
    assert format_price(350) == "350"
    assert format_price(350.0) == "350"
    assert format_price(12.75) == "12.75"


def test_format_trip_escapes_html():
    trip = make_trip(name="<b>Иван</b>", from_address="A & B")
    text = format_trip(trip, 1)
    assert "&lt;b&gt;Иван&lt;/b&gt;" in text
    assert "A &amp; B" in text
    assert "12.5 км" in text
    assert "3 мин" in text
    assert "350 р." in text
    assert datetime.fromtimestamp(trip.time).strftime("%d.%m.%Y %H:%M") in text


def test_balance_message_orders_newest_first():
    trips = [make_trip(time=100, name="старая"), make_trip(time=200, name="новая")]
    text = format_balance_message(1500, trips)
    assert text.index("новая") < text.index("старая")
    assert "1. " in text and "2. " in text
    assert "Баланс:</b> 1500 р." in text


def test_balance_message_without_trips():
    text = format_balance_message(None, [])
    assert NO_TRIPS_TEMPLATE in text
    assert "0 р." in text


def test_format_last_update_uses_timezone():
    text = format_last_update(0, ZoneInfo("Europe/Moscow"))
    assert "01.01.1970 03:00" in text


def test_truncate():
    assert truncate("short", limit=10) == "short"
    long = "x" * 100
    cut = truncate(long, limit=50)
    assert len(cut) == 50
    assert cut.endswith(MSG_TRUNCATED)
