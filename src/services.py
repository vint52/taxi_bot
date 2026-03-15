"""Business logic services."""
from datetime import datetime
from html import escape
from typing import Dict, List, Optional
import logging

from database import RedisDatabase
from taxi import Taxi, TaxiScraperError
from constants import (
    BALANCE_TEMPLATE,
    NO_TRIPS_TEMPLATE,
    RECENT_TRIPS_COUNT,
    TRIP_TEMPLATE,
)


logger = logging.getLogger(__name__)


class TaxiService:
    """Service for taxi-related operations."""
    
    def __init__(self, db: RedisDatabase, taxi_client: Taxi):
        """Initialize the service."""
        self.db = db
        self.taxi_client = taxi_client
    
    def format_trip(self, trip: Dict, index: int) -> str:
        """Format a single trip for display."""
        try:
            return TRIP_TEMPLATE.format(
                index=index,
                time=escape(datetime.fromtimestamp(trip['time']).strftime('%d.%m.%Y %H:%M')),
                name=escape(str(trip['name'])),
                phone=escape(str(trip['phone'])),
                from_address=escape(str(trip['from'])),
                to_address=escape(str(trip['to'])),
                distance=self._format_decimal(trip['distance']),
                waiting=self._format_decimal(trip['waiting'], decimals=1),
                price=self._format_price(trip['price']),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error formatting trip {trip}: {e}")
            return f"Ошибка форматирования поездки: {e}"
    
    def make_balance_message(self) -> str:
        """Create a message with balance and recent trips."""
        try:
            balance = self._format_price(self.db.get_balance() or "0")
            trips = self.db.get_recent_trips(RECENT_TRIPS_COUNT)
            
            # Format trips in reverse chronological order
            formatted_trips = self._format_trips(trips)
            
            return BALANCE_TEMPLATE.format(balance=escape(balance), trips=formatted_trips)
        except Exception as e:
            logger.error(f"Error creating balance message: {e}")
            return f"Ошибка получения данных: {escape(str(e))}"
    
    def _format_trips(self, trips: List[Dict]) -> str:
        """Format list of trips for display."""
        if not trips:
            return NO_TRIPS_TEMPLATE

        formatted_trips = []
        for index, trip in enumerate(reversed(trips), start=1):
            formatted_trips.append(self.format_trip(trip, index))
        return '\n\n'.join(formatted_trips)

    def _format_decimal(self, value: object, decimals: int = 2) -> str:
        """Format decimal values without trailing zero noise."""
        number = float(value)
        formatted = f"{number:.{decimals}f}".rstrip('0').rstrip('.')
        return formatted or "0"

    def _format_price(self, value: object) -> str:
        """Format price values as integers when possible."""
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return self._format_decimal(number, decimals=2)
    
    def update_data(self) -> bool:
        """
        Update taxi data from the service.
        
        Returns:
            True if data was updated, False otherwise.
            
        Raises:
            TaxiScraperError: If taxi service fails
        """
        try:
            logger.debug('Starting data update from taxi service')
            result = self._fetch_taxi_data()
            
            has_updates = False
            has_updates |= self._update_balance(result['balance'])
            has_updates |= self._update_trips(result['trips'])
            
            # Update timestamp
            self.db.set_timestamp()
            logger.debug(f'Data update completed, has_updates={has_updates}')
            
            return has_updates
            
        except TaxiScraperError:
            raise
        except Exception as e:
            logger.error(f'Unexpected error updating data: {e}', exc_info=True)
            raise TaxiScraperError(f"Failed to update data: {e}") from e
    
    def _fetch_taxi_data(self) -> Dict:
        """Fetch data from taxi service."""
        try:
            result = self.taxi_client.get_profile_info()
            logger.debug(f'Retrieved profile info: balance={result["balance"]}, trips_count={len(result["trips"])}')
            return result
        except TaxiScraperError as e:
            logger.error(f'TaxiScraperError fetching taxi data: {e}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error fetching taxi data: {e}', exc_info=True)
            raise TaxiScraperError(f"Failed to fetch taxi data: {e}") from e
    
    def _update_balance(self, new_balance: int) -> bool:
        """Update balance if changed."""
        try:
            old_balance = self.db.get_balance()
            logger.debug(f'Balance check: old={old_balance}, new={new_balance}')
            
            if old_balance is None or int(old_balance) != int(new_balance):
                logger.info(f'Balance updated: {new_balance}')
                self.db.set_balance(new_balance)
                return True
            
            return False
        except Exception as e:
            logger.error(f'Error updating balance: {e}')
            raise
    
    def _update_trips(self, new_trips: List[Dict]) -> bool:
        """Update trips if changed."""
        try:
            last_trip = self.db.get_last_trip()
            logger.debug(f'Trips check: last_trip={last_trip}, new_trips_count={len(new_trips)}')
            
            if new_trips and (not last_trip or last_trip['time'] != new_trips[-1]['time']):
                logger.info('Trips updated')
                logger.debug(f'Adding {len(new_trips)} new trips to database')
                for trip in new_trips:
                    self.db.add_trip(trip)
                return True
            
            return False
        except Exception as e:
            logger.error(f'Error updating trips: {e}')
            raise

