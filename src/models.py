"""Domain models shared between the scraper, storage and formatting layers."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Trip:
    """A single completed taxi ride."""

    time: int  # unix timestamp of the ride
    phone: str
    name: str
    from_address: str
    to_address: str
    distance: float  # kilometres
    waiting: float  # minutes
    price: int  # roubles

    def to_json(self) -> str:
        """Serialise for storage. Key order and names are part of the storage format."""
        return json.dumps(
            {
                "time": self.time,
                "phone": self.phone,
                "name": self.name,
                "from": self.from_address,
                "to": self.to_address,
                "distance": self.distance,
                "waiting": self.waiting,
                "price": self.price,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, raw: str) -> Trip:
        """Restore a trip from its stored JSON representation."""
        data = json.loads(raw)
        return cls(
            time=int(data["time"]),
            phone=str(data["phone"]),
            name=str(data["name"]),
            from_address=str(data["from"]),
            to_address=str(data["to"]),
            distance=float(data["distance"]),
            waiting=float(data["waiting"]),
            price=int(data["price"]),
        )


@dataclass(frozen=True, slots=True)
class ProfileInfo:
    """Snapshot of the corporate cabinet: balance and the rides listed on the page."""

    balance: int
    trips: list[Trip]
