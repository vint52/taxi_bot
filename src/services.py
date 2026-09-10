"""Application logic: syncing the cabinet into storage and rendering it for users."""

from __future__ import annotations

import asyncio
import logging
from zoneinfo import ZoneInfo

from constants import RECENT_TRIPS_COUNT
from database import Storage
from formatting import format_balance_message, format_last_update
from models import Trip
from taxi import TaxiClient

logger = logging.getLogger(__name__)


class TaxiService:
    """Keeps storage in sync with the cabinet and builds the balance message."""

    def __init__(self, storage: Storage, client: TaxiClient, tz: ZoneInfo) -> None:
        self._storage = storage
        self._client = client
        self._tz = tz

    async def update_data(self) -> bool:
        """Poll the cabinet and persist changes. Returns True when something changed."""
        info = await asyncio.to_thread(self._client.get_profile_info)
        logger.debug("Cabinet reports balance=%s, trips=%d", info.balance, len(info.trips))

        changed = await self._update_balance(info.balance)
        changed = await self._update_trips(info.trips) or changed
        await self._storage.set_timestamp()
        return changed

    async def make_balance_message(self, with_update_time: bool = False) -> str:
        """Render balance and recent rides; optionally append the last sync time."""
        balance = await self._storage.get_balance()
        trips = await self._storage.get_recent_trips(RECENT_TRIPS_COUNT)
        text = format_balance_message(balance, trips)
        if with_update_time and (timestamp := await self._storage.get_timestamp()):
            text += format_last_update(timestamp, self._tz)
        return text

    async def _update_balance(self, balance: int) -> bool:
        if await self._storage.get_balance() == balance:
            return False
        logger.info("Balance changed to %s", balance)
        await self._storage.set_balance(balance)
        return True

    async def _update_trips(self, trips: list[Trip]) -> bool:
        if not trips:
            return False
        last = await self._storage.get_last_trip()
        if last is not None and last.time == trips[-1].time:
            return False
        logger.info("New trips found, storing %d rows", len(trips))
        await self._storage.add_trips(trips)
        return True
