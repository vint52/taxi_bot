"""Main bot handlers coordinator."""
from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from constants import BTN_LOGS, BTN_USERS
from database import RedisDatabase
from services import TaxiService
from .admin_handlers import AdminHandlers
from .callback_handlers import CallbackHandlers
from .user_handlers import UserHandlers


class BotHandlers:
    """Main bot handlers coordinator."""
    
    def __init__(self, config: Config, db: RedisDatabase, taxi_service: TaxiService):
        """Initialize handlers."""
        self.config = config
        self.db = db
        self.taxi_service = taxi_service
        self.router = Router(name=__name__)
        
        # Initialize handler components
        self.admin_handlers = AdminHandlers(config, db, taxi_service)
        self.user_handlers = UserHandlers(config, db, taxi_service)
        self.callback_handlers = CallbackHandlers(config, db, taxi_service)
        self._register_routes()
    
    # Delegate to appropriate handlers
    async def start_handler(self, message: Message) -> None:
        """Handle /start and /help commands."""
        await self.user_handlers.start_handler(message)
    
    async def logs_handler(self, message: Message) -> None:
        """Handle logs request (admin only)."""
        await self.admin_handlers.logs_handler(message)
    
    async def users_handler(self, message: Message) -> None:
        """Handle users list request (admin only)."""
        await self.admin_handlers.users_handler(message)
    
    async def balance_handler(self, message: Message) -> None:
        """Handle balance check request."""
        await self.user_handlers.balance_handler(message)
    
    async def delete_user_handler(self, message: Message) -> None:
        """Handle /delete command (admin only)."""
        await self.admin_handlers.delete_user_handler(message)
    
    async def user_logs_handler(self, message: Message) -> None:
        """Handle /logs command (admin only)."""
        await self.admin_handlers.user_logs_handler(message)
    
    async def user_callback_handler(self, callback_query: CallbackQuery) -> None:
        """Handle user selection callback."""
        await self.callback_handlers.user_callback_handler(callback_query)
    
    async def unknown_handler(self, message: Message) -> None:
        """Handle unknown commands."""
        await self.user_handlers.unknown_handler(message)
    
    def _register_routes(self) -> None:
        """Register all handlers on the router."""
        from constants import BTN_CHECK_BALANCE

        self.router.message.register(self.start_handler, CommandStart())
        self.router.message.register(self.start_handler, Command("help"))
        self.router.message.register(self.delete_user_handler, Command("delete"))
        self.router.message.register(self.user_logs_handler, Command("logs"))
        self.router.message.register(self.logs_handler, F.text == BTN_LOGS)
        self.router.message.register(self.users_handler, F.text == BTN_USERS)
        self.router.message.register(
            self.balance_handler,
            F.text == BTN_CHECK_BALANCE,
        )
        self.router.callback_query.register(self.user_callback_handler)
        self.router.message.register(self.unknown_handler)

    def register_handlers(self, dp: Dispatcher) -> None:
        """Register the composed router on the dispatcher."""
        dp.include_router(self.router)
