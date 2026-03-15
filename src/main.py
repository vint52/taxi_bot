"""Main entry point for the Taxi Bot."""
import asyncio
from contextlib import suppress
import logging
import sys

from aiogram import Bot, Dispatcher

from config import Config
from database import RedisDatabase
from handlers import BotHandlers
from logging_config import setup_logging
from scheduler import UpdateScheduler
from services import TaxiService
from taxi import Taxi, TaxiAuthenticationError


logger = logging.getLogger(__name__)


class TaxiBot:
    """Main bot application."""
    
    def __init__(self, config: Config):
        """Initialize the bot."""
        self.config = config
        self._initialize_components()
        self._register_handlers()
    
    def _initialize_components(self) -> None:
        """Initialize all bot components."""
        # Initialize core components
        self.bot = Bot(token=self.config.tg_token)
        self.dp = Dispatcher()
        self.db = RedisDatabase(self.config)
        self.scheduler_task: asyncio.Task | None = None
        
        # Initialize taxi client
        try:
            self.taxi_client = Taxi(
                self.config.taxi_username,
                self.config.taxi_password,
                debug_html_dir=self.config.debug_html_dir
            )
        except TaxiAuthenticationError as e:
            logger.error(f"Failed to authenticate with taxi service: {e}")
            raise
        
        # Initialize services
        self.taxi_service = TaxiService(self.db, self.taxi_client)
        self.handlers = BotHandlers(self.config, self.db, self.taxi_service)
        self.scheduler = UpdateScheduler(self.config, self.db, self.taxi_service, self.bot)
    
    def _register_handlers(self) -> None:
        """Register all bot handlers."""
        self.handlers.register_handlers(self.dp)
    
    async def send_updates_to_all_users(self) -> None:
        """Send updates to all registered users."""
        logger.debug("Preparing to send updates to all users")
        msg = self.taxi_service.make_balance_message()
        users = self.db.get_users()
        logger.debug(f"Found {len(users)} registered users: {list(users)}")
        
        for user_id in users:
            try:
                user_id_int = int(user_id)
                logger.info(f'Sending update to user {user_id}')
                logger.debug(f'Sending message to user {user_id}, message length: {len(msg)}')
                await self.bot.send_message(user_id_int, msg, parse_mode="HTML")
                logger.debug(f'Successfully sent update to user {user_id}')
            except Exception as e:
                logger.error(f'Failed to send message to user {user_id}: {e}')
                logger.debug(f'Failed to send message to user {user_id}, error type: {type(e).__name__}')
    
    async def on_startup(self) -> None:
        """Handler called when bot starts."""
        logger.info("Bot is starting up...")
        self.scheduler_task = asyncio.create_task(self.scheduler.start())
        logger.info(f"Update scheduler started (interval: {self.config.taxi_update_period}s)")
    
    async def on_shutdown(self) -> None:
        """Handler called when bot shuts down."""
        logger.info("Bot is shutting down...")
        await self.scheduler.stop()
        if self.scheduler_task:
            self.scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.scheduler_task

    async def start(self) -> None:
        """Start the bot."""
        logger.info("Starting Taxi Bot...")
        await self.on_startup()
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(self.bot)
        finally:
            await self.on_shutdown()


async def run() -> None:
    """Create and run the bot."""
    config = Config.from_env()
    setup_logging(config.tg_log_path)
    bot = TaxiBot(config)
    await bot.start()


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(run())
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except TaxiAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
