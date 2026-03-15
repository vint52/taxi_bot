"""User-specific handlers."""
import logging
from datetime import datetime

import pytz
from aiogram.types import Message, ReplyKeyboardMarkup

from config import Config
from database import RedisDatabase
from services import TaxiService
from constants import (
    MSG_COMMAND_NOT_FOUND,
    MSG_PRIVATE_BOT,
    MSG_SECRET_CODE_ACCEPTED,
    MSG_WELCOME,
)
from .common import build_main_keyboard


logger = logging.getLogger(__name__)


class UserHandlers:
    """User-specific message handlers."""
    
    def __init__(self, config: Config, db: RedisDatabase, taxi_service: TaxiService):
        """Initialize user handlers."""
        self.config = config
        self.db = db
        self.taxi_service = taxi_service
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.config.tg_admin_id
    
    def get_keyboard(self, user_id: int) -> ReplyKeyboardMarkup:
        """Create keyboard based on user permissions."""
        return build_main_keyboard(self.is_admin(user_id))
    
    def is_private_bot(self) -> bool:
        """Check if bot requires secret code for new users."""
        return bool(self.config.bot_secret_code)

    async def start_handler(self, message: Message) -> None:
        """Handle /start and /help commands."""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        logger.info(f'USER_START - User {user_id} ({username}) started the bot')
        
        # Check if user already exists
        if self.db.user_exists(user_id):
            logger.info(f'USER_EXISTING - User {user_id} ({username}) is already registered')
            keyboard = self.get_keyboard(user_id)
            await message.answer(MSG_WELCOME, reply_markup=keyboard)
            return
        
        # Check if bot is private and requires secret code
        if self.is_private_bot():
            logger.info(f'USER_NEW_PRIVATE - New user {user_id} ({username}) needs secret code')
            await message.answer(MSG_PRIVATE_BOT)
            return
        
        # Public bot - register user immediately
        logger.info(f'USER_REGISTRATION - User {user_id} ({username}) registered')
        self.db.add_user(user_id)
        keyboard = self.get_keyboard(user_id)
        await message.answer(MSG_WELCOME, reply_markup=keyboard)
    
    async def balance_handler(self, message: Message) -> None:
        """Handle balance check request."""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        # Check if user is authorized
        if self.is_private_bot() and not self.db.user_exists(user_id):
            logger.info(
                f'USER_UNAUTHORIZED - User {user_id} ({username}) '
                f'tried to access balance without authorization'
            )
            await message.answer(MSG_PRIVATE_BOT)
            return
        
        # Ensure user is in database
        if not self.db.user_exists(user_id):
            self.db.add_user(user_id)
        
        logger.info(f'USER_ACTION - User {user_id} ({username}) pressed "Check balance" button')
        
        keyboard = self.get_keyboard(user_id)
        msg = self.taxi_service.make_balance_message()
        
        # Add last update time for admin
        if self.is_admin(user_id):
            logger.info(f'ADMIN_ACTION - Admin {user_id} ({username}) requested balance with admin info')
            msg = await self._add_admin_info(msg)
        
        await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
    
    async def _add_admin_info(self, msg: str) -> str:
        """Add admin-specific information to message."""
        timestamp = self.db.get_timestamp()
        
        if timestamp:
            last_time = datetime.fromtimestamp(
                timestamp, 
                pytz.timezone('Europe/Moscow')
            ).strftime('%d.%m.%Y %H:%M')
            msg += f'\n\n<i>Last update: {last_time}</i>'
        
        return msg
    
    async def unknown_handler(self, message: Message) -> None:
        """Handle unknown commands."""
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        # Check if this is a new user trying to enter secret code
        if self.is_private_bot() and not self.db.user_exists(user_id):
            # Check if the message matches the secret code
            if message.text and message.text.strip() == self.config.bot_secret_code:
                logger.info(
                    f'USER_REGISTRATION - User {user_id} ({username}) '
                    f'entered correct secret code and registered'
                )
                self.db.add_user(user_id)
                keyboard = self.get_keyboard(user_id)
                await message.answer(MSG_SECRET_CODE_ACCEPTED, reply_markup=keyboard)
                await message.answer(MSG_WELCOME, reply_markup=keyboard)
                return
            else:
                # Invalid secret code - do nothing (silent ignore)
                logger.info(
                    f'USER_UNAUTHORIZED - User {user_id} ({username}) '
                    f'entered invalid secret code'
                )
                return
        
        logger.info(f'USER_ACTION - User {user_id} ({username}) sent unknown command: "{message.text}"')
        keyboard = self.get_keyboard(user_id)
        await message.reply(MSG_COMMAND_NOT_FOUND, reply_markup=keyboard)
