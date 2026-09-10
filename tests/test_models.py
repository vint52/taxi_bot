import json

from conftest import make_trip
from models import Trip


def test_json_roundtrip():
    trip = make_trip()
    assert Trip.from_json(trip.to_json()) == trip


def test_json_format_matches_stored_layout():
    """Stored members must keep the historic key order and names."""
    raw = make_trip().to_json()
    expected = json.dumps(
        {
            "time": 1_700_000_000,
            "phone": "+79990000000",
            "name": "Иван",
            "from": "ул. Ленина, 1",
            "to": "пр. Мира, 5",
            "distance": 12.5,
            "waiting": 3.0,
            "price": 350,
        },
        ensure_ascii=False,
    )
    assert raw == expected
