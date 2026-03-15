"""Database (Redis) abstraction layer."""
import json
import logging
import time
from typing import Dict, List, Optional, Set

import redis
from redis.exceptions import ConnectionError, RedisError

from config import Config
from constants import (
    REDIS_KEY_BALANCE,
    REDIS_KEY_TRIPS,
    REDIS_KEY_USERS,
    REDIS_KEY_TIMESTAMP
)

logger = logging.getLogger(__name__)


class RedisDatabase:
    """Redis database wrapper."""
    
    def __init__(self, config: Config):
        """Initialize Redis connection."""
        try:
            self.client = redis.Redis(
                host=config.redis_host,
                password=config.redis_password,
                port=config.redis_port,
                db=config.redis_db,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self.client.ping()
            logger.info("Redis connection established successfully")
        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get_balance(self) -> Optional[str]:
        """Get current balance."""
        try:
            balance = self.client.get(REDIS_KEY_BALANCE)
            logger.debug(f'Retrieved balance from Redis: {balance}')
            return balance
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error getting balance: {e}')
            raise
    
    def set_balance(self, balance: int) -> None:
        """Set balance value."""
        try:
            logger.debug(f'Setting balance in Redis: {balance}')
            self.client.set(REDIS_KEY_BALANCE, balance)
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error setting balance: {e}')
            raise
    
    def get_recent_trips(self, count: int = 3) -> List[Dict]:
        """Get recent trips."""
        try:
            trips_raw = self.client.zrange(REDIS_KEY_TRIPS, -count, -1)
            logger.debug(f'Retrieved {len(trips_raw)} recent trips from Redis')
            return [self._parse_trip(trip) for trip in trips_raw]
        except (RedisError, ConnectionError, json.JSONDecodeError) as e:
            logger.error(f'Error getting recent trips: {e}')
            raise
    
    def get_last_trip(self) -> Optional[Dict]:
        """Get the most recent trip."""
        try:
            trips = self.client.zrange(REDIS_KEY_TRIPS, -1, -1)
            if trips:
                return self._parse_trip(trips[0])
            return None
        except (RedisError, ConnectionError, json.JSONDecodeError) as e:
            logger.error(f'Error getting last trip: {e}')
            raise
    
    def add_trip(self, trip: Dict) -> None:
        """Add a trip to the database."""
        try:
            self.client.zadd(
                REDIS_KEY_TRIPS,
                {json.dumps(trip, ensure_ascii=False): trip['time']}
            )
        except (RedisError, ConnectionError, TypeError) as e:
            logger.error(f'Error adding trip: {e}')
            raise
    
    def _parse_trip(self, trip_data: str) -> Dict:
        """Parse trip data from JSON."""
        try:
            return json.loads(trip_data)
        except json.JSONDecodeError as e:
            logger.error(f'Error parsing trip data: {e}')
            raise
    
    def add_user(self, user_id: int) -> None:
        """Add a user to the database."""
        try:
            logger.debug(f'Adding user {user_id} to Redis set {REDIS_KEY_USERS}')
            result = self.client.sadd(REDIS_KEY_USERS, str(user_id))
            logger.debug(f'User {user_id} added to Redis, result: {result}')
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error adding user {user_id}: {e}')
            raise

    def user_exists(self, user_id: int) -> bool:
        """Check if user exists in the database."""
        try:
            exists = self.client.sismember(REDIS_KEY_USERS, str(user_id))
            logger.debug(f'User {user_id} exists check: {exists}')
            return exists
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error checking user {user_id}: {e}')
            raise
    
    def get_users(self) -> Set[str]:
        """Get all users."""
        try:
            logger.debug(f'Getting users from Redis set {REDIS_KEY_USERS}')
            users = self.client.smembers(REDIS_KEY_USERS)
            logger.debug(f'Retrieved users from Redis: {users}, type: {type(users)}')
            return users
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error getting users: {e}')
            raise
    
    def remove_user(self, user_id: int) -> bool:
        """
        Remove a user from the database.
        
        Args:
            user_id: User ID to remove
            
        Returns:
            True if user was removed, False if user didn't exist
        """
        try:
            result = self.client.srem(REDIS_KEY_USERS, str(user_id))
            return result > 0
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error removing user {user_id}: {e}')
            raise
    
    def get_timestamp(self) -> int:
        """Get last update timestamp."""
        try:
            ts = self.client.get(REDIS_KEY_TIMESTAMP)
            return int(ts) if ts else 0
        except (RedisError, ConnectionError, ValueError) as e:
            logger.error(f'Error getting timestamp: {e}')
            raise
    
    def set_timestamp(self, timestamp: Optional[int] = None) -> None:
        """Set update timestamp."""
        try:
            if timestamp is None:
                timestamp = int(time.time())
            self.client.set(REDIS_KEY_TIMESTAMP, timestamp)
        except (RedisError, ConnectionError) as e:
            logger.error(f'Error setting timestamp: {e}')
            raise

