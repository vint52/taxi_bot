"""Redis-backed storage for balance, rides and registered users."""

from __future__ import annotations

import time
from collections.abc import Iterable

from redis.asyncio import Redis

from config import Config
from models import Trip

KEY_BALANCE = "balance"
KEY_TRIPS = "trips"
KEY_USERS = "users"
KEY_TIMESTAMP = "timestamp"


class Storage:
    """Thin async wrapper over the handful of Redis keys the bot uses."""

    def __init__(self, client: Redis) -> None:
        self._redis = client

    @classmethod
    def from_config(cls, config: Config) -> Storage:
        """Create a storage connected according to ``config``."""
        client = Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        return cls(client)

    async def ping(self) -> None:
        """Fail fast if Redis is unreachable."""
        await self._redis.ping()

    async def close(self) -> None:
        await self._redis.aclose()

    # --- balance -------------------------------------------------------

    async def get_balance(self) -> int | None:
        raw = await self._redis.get(KEY_BALANCE)
        return int(raw) if raw is not None else None

    async def set_balance(self, balance: int) -> None:
        await self._redis.set(KEY_BALANCE, balance)

    # --- trips ---------------------------------------------------------

    async def get_recent_trips(self, count: int) -> list[Trip]:
        """Return up to ``count`` latest rides, oldest first."""
        raw = await self._redis.zrange(KEY_TRIPS, -count, -1)
        return [Trip.from_json(item) for item in raw]

    async def get_last_trip(self) -> Trip | None:
        trips = await self.get_recent_trips(1)
        return trips[0] if trips else None

    async def add_trips(self, trips: Iterable[Trip]) -> None:
        """Store rides keyed by their timestamp; identical rides are not duplicated."""
        mapping = {trip.to_json(): trip.time for trip in trips}
        if mapping:
            await self._redis.zadd(KEY_TRIPS, mapping)

    # --- users ---------------------------------------------------------

    async def add_user(self, user_id: int) -> bool:
        """Register a user; returns False if they were already registered."""
        return await self._redis.sadd(KEY_USERS, str(user_id)) > 0

    async def user_exists(self, user_id: int) -> bool:
        return bool(await self._redis.sismember(KEY_USERS, str(user_id)))

    async def get_users(self) -> set[int]:
        return {int(user_id) for user_id in await self._redis.smembers(KEY_USERS)}

    async def remove_user(self, user_id: int) -> bool:
        """Unregister a user; returns False if they were not registered."""
        return await self._redis.srem(KEY_USERS, str(user_id)) > 0

    # --- bookkeeping ---------------------------------------------------

    async def get_timestamp(self) -> int:
        raw = await self._redis.get(KEY_TIMESTAMP)
        return int(raw) if raw else 0

    async def set_timestamp(self, timestamp: int | None = None) -> None:
        await self._redis.set(
            KEY_TIMESTAMP, timestamp if timestamp is not None else int(time.time())
        )
