"""Scheduler module for periodic tasks."""
import asyncio
import logging
from typing import Optional

from aiogram import Bot

from config import Config
from database import RedisDatabase
from services import TaxiService


logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Handles periodic updates of taxi data."""
    
    def __init__(self, config: Config, db: RedisDatabase, taxi_service: TaxiService, bot: Optional[Bot] = None):
        """Initialize the scheduler."""
        self.config = config
        self.db = db
        self.taxi_service = taxi_service
        self.bot = bot
        self._running = False
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        logger.info(f"Starting update scheduler with period: {self.config.taxi_update_period}s")
        
        try:
            await self._run_scheduler_loop()
        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled")
            raise
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            raise
        finally:
            self._running = False
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("Scheduler stopped")
    
    async def _run_scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._perform_update()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            
            if self._running:
                logger.debug(f"Sleeping for {self.config.taxi_update_period} seconds")
                await asyncio.sleep(self.config.taxi_update_period)
    
    async def _perform_update(self) -> None:
        """Perform a single update cycle."""
        logger.debug("SCHEDULER_ACTION - Running scheduled update...")
        
        try:
            has_updates = self.taxi_service.update_data()
            
            if has_updates:
                logger.info("SCHEDULER_ACTION - Data updated, notifying users...")
                await self._notify_users()
            else:
                logger.debug("SCHEDULER_ACTION - No updates found")
                
        except Exception as e:
            logger.error(f"SCHEDULER_ERROR - Error during update: {e}", exc_info=True)
            # Don't raise - continue scheduler loop even if update fails
            # This allows the scheduler to retry on next cycle
    
    async def _notify_users(self) -> None:
        """Notify all users about updates."""
        if not self.bot:
            logger.warning("Bot instance not available, cannot send notifications")
            return
        
        try:
            msg = self.taxi_service.make_balance_message()
            users = self.db.get_users()
            
            logger.info(f"SCHEDULER_ACTION - Notifying {len(users)} users about balance update")
            
            for user_id in users:
                try:
                    user_id_int = int(user_id)
                    await self.bot.send_message(user_id_int, msg, parse_mode="HTML")
                    logger.info(f"SCHEDULER_ACTION - Successfully sent update to user {user_id}")
                except Exception as e:
                    logger.error(f"SCHEDULER_ERROR - Failed to send message to user {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"SCHEDULER_ERROR - Error notifying users: {e}", exc_info=True)
            raise
