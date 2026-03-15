"""Admin-specific handlers."""
import logging

from aiogram.types import Message, ReplyKeyboardMarkup

from config import Config
from database import RedisDatabase
from services import TaxiService
from constants import (
    MSG_CANNOT_DELETE_SELF,
    MSG_DELETE_USAGE,
    MSG_INVALID_USER_ID,
    MSG_LOGS_DISABLED,
    MSG_NO_LOGS_FOR_USER,
    MSG_NO_USERS,
    MSG_REDIS_CONNECTION_ERROR,
    MSG_TEST_USER_ADDED,
    MSG_TEST_USER_EXISTS,
    MSG_USER_DELETED,
    MSG_USER_LOGS_HEADER,
    MSG_USER_LOGS_USAGE,
    MSG_USER_NOT_FOUND,
    MSG_USERS_LIST_HEADER,
    LOG_LINES_TO_SHOW,
)
from utils import read_last_log_lines, filter_logs_by_user, get_user_activity_summary
from .common import build_main_keyboard, build_users_inline_keyboard


logger = logging.getLogger(__name__)


class AdminHandlers:
    """Admin-specific message handlers."""
    
    def __init__(self, config: Config, db: RedisDatabase, taxi_service: TaxiService):
        """Initialize admin handlers."""
        self.config = config
        self.db = db
        self.taxi_service = taxi_service
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.config.tg_admin_id
    
    def get_keyboard(self, user_id: int) -> ReplyKeyboardMarkup:
        """Create keyboard based on user permissions."""
        return build_main_keyboard(self.is_admin(user_id))
    
    async def logs_handler(self, message: Message) -> None:
        """Handle logs request (admin only)."""
        if not self.is_admin(message.from_user.id):
            return
        
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        logger.info(f'ADMIN_ACTION - Admin {user_id} ({username}) pressed "Show logs" button')
        keyboard = self.get_keyboard(user_id)
        
        if self.config.tg_log_path:
            logs = read_last_log_lines(self.config.tg_log_path, LOG_LINES_TO_SHOW)
            await message.answer(logs, reply_markup=keyboard)
        else:
            await message.answer(MSG_LOGS_DISABLED, reply_markup=keyboard)
    
    async def users_handler(self, message: Message) -> None:
        """Handle users list request (admin only)."""
        if not self.is_admin(message.from_user.id):
            return
        
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        logger.info(f'ADMIN_ACTION - Admin {user_id} ({username}) pressed "Show users" button')
        
        # Add current user to database if not exists
        self.db.add_user(user_id)
        
        users = self.db.get_users()
        
        if users and len(users) > 0:
            await self._show_users_list(message, users)
        else:
            await self._show_empty_users_debug(message)
    
    async def _show_users_list(self, message: Message, users) -> None:
        """Show users list with inline keyboard."""
        await message.answer(
            MSG_USERS_LIST_HEADER + "Нажмите на пользователя для управления:",
            reply_markup=build_users_inline_keyboard(users)
        )
    
    async def _show_empty_users_debug(self, message: Message) -> None:
        """Show debug information for empty users list."""
        debug_msg = f"{MSG_NO_USERS}\n\n🔍 Отладочная информация:\n"
        debug_msg += f"• Текущий пользователь: {message.from_user.id}\n"
        debug_msg += f"• Администратор: {self.is_admin(message.from_user.id)}\n"
        debug_msg += f"• Redis подключение: {'✅' if self.db.client.ping() else '❌'}\n"
        debug_msg += f"• Количество пользователей: {len(self.db.get_users())}\n"
        debug_msg += f"• Попробуйте отправить /start для добавления пользователя"
        
        keyboard = self.get_keyboard(message.from_user.id)
        await message.answer(debug_msg, reply_markup=keyboard)
    
    async def delete_user_handler(self, message: Message) -> None:
        """Handle /delete command (admin only)."""
        if not self.is_admin(message.from_user.id):
            return
        
        # Parse command: /delete {user_id}
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await message.reply(MSG_DELETE_USAGE)
            return
        
        try:
            user_id_to_delete = int(command_parts[1])
        except ValueError:
            await message.reply(MSG_INVALID_USER_ID)
            return
        
        # Check if trying to delete self
        if user_id_to_delete == message.from_user.id:
            await message.reply(MSG_CANNOT_DELETE_SELF)
            return
        
        # Remove user from database
        success = self.db.remove_user(user_id_to_delete)
        
        if success:
            logger.info(f'User {user_id_to_delete} deleted by admin {message.from_user.id}')
            await message.reply(MSG_USER_DELETED.format(user_id=user_id_to_delete))
        else:
            await message.reply(MSG_USER_NOT_FOUND.format(user_id=user_id_to_delete))
    
    async def user_logs_handler(self, message: Message) -> None:
        """Handle /logs command (admin only)."""
        if not self.is_admin(message.from_user.id):
            return
        
        # Parse command: /logs {user_id}
        command_parts = message.text.split()
        if len(command_parts) != 2:
            await message.reply(MSG_USER_LOGS_USAGE)
            return
        
        try:
            user_id_to_search = int(command_parts[1])
        except ValueError:
            await message.reply(MSG_INVALID_USER_ID)
            return
        
        # Check if log file is configured
        if not self.config.tg_log_path:
            await message.reply(MSG_LOGS_DISABLED)
            return
        
        await self._show_user_logs(message, user_id_to_search)
    
    async def _show_user_logs(self, message: Message, user_id: int) -> None:
        """Show user logs with activity summary."""
        # Get user activity summary
        summary = get_user_activity_summary(self.config.tg_log_path, user_id)
        
        if "error" in summary:
            await message.reply(summary["error"])
            return
        
        # Get filtered logs
        user_logs = filter_logs_by_user(self.config.tg_log_path, user_id, max_lines=30)
        
        if not user_logs.strip():
            await message.reply(MSG_NO_LOGS_FOR_USER.format(user_id=user_id))
            return
        
        # Create response message
        response = await self._build_user_logs_response(user_id, summary, user_logs)
        
        # Split message if too long (Telegram limit is 4096 chars)
        if len(response) > 4000:
            await self._send_split_user_logs(message, user_id, summary, user_logs)
        else:
            await message.reply(response)
        
        logger.info(f'User logs requested for {user_id} by admin {message.from_user.id}')
    
    async def _build_user_logs_response(self, user_id: int, summary: dict, user_logs: str) -> str:
        """Build user logs response message."""
        response = MSG_USER_LOGS_HEADER.format(user_id=user_id) + "\n\n"
        
        # Add activity summary
        response += f"📊 Статистика активности:\n"
        response += f"• Всего записей: {summary['total_entries']}\n"
        response += f"• Запусков бота: {summary['activities']['start']}\n"
        response += f"• Проверок баланса: {summary['activities']['balance']}\n"
        response += f"• Просмотров логов: {summary['activities']['logs']}\n"
        response += f"• Просмотров пользователей: {summary['activities']['users']}\n"
        response += f"• Неизвестных команд: {summary['activities']['unknown']}\n\n"
        
        if summary['last_activity']:
            response += f"🕐 Последняя активность:\n{summary['last_activity']}\n\n"
        
        response += "📝 Последние логи:\n"
        response += user_logs
        
        return response
    
    async def _send_split_user_logs(self, message: Message, user_id: int, summary: dict, user_logs: str) -> None:
        """Send user logs in multiple messages if too long."""
        # Send summary first
        summary_msg = MSG_USER_LOGS_HEADER.format(user_id=user_id) + "\n\n"
        summary_msg += f"📊 Статистика: {summary['total_entries']} записей\n"
        summary_msg += f"• Запусков: {summary['activities']['start']}\n"
        summary_msg += f"• Баланс: {summary['activities']['balance']}\n"
        summary_msg += f"• Логи: {summary['activities']['logs']}\n"
        summary_msg += f"• Пользователи: {summary['activities']['users']}\n"
        summary_msg += f"• Неизвестные: {summary['activities']['unknown']}\n\n"
        
        if summary['last_activity']:
            summary_msg += f"🕐 Последняя активность:\n{summary['last_activity']}"
        
        await message.reply(summary_msg)
        
        # Send logs separately
        await message.reply("📝 Логи:\n" + user_logs)
    
    async def add_test_user_handler(self, message: Message) -> None:
        """Handle /addtestuser command (admin only)."""
        if not self.is_admin(message.from_user.id):
            return
        
        logger.info(f'Add test user - {message.from_user.username} ({message.from_user.id})')
        keyboard = self.get_keyboard(message.from_user.id)
        
        try:
            # Test Redis connection
            if not self.db.client.ping():
                await message.reply(MSG_REDIS_CONNECTION_ERROR, reply_markup=keyboard)
                return
            
            # Add test user
            test_user_id = 123456789
            self.db.add_user(test_user_id)
            
            # Check if user was added
            users = self.db.get_users()
            logger.debug(f'Users after adding test user: {users}')
            if users and str(test_user_id) in users:
                await message.reply(MSG_TEST_USER_ADDED, reply_markup=keyboard)
            else:
                await message.reply(MSG_TEST_USER_EXISTS, reply_markup=keyboard)
                
        except Exception as e:
            logger.error(f'Error adding test user: {e}')
            await message.reply(f"❌ Ошибка: {e}", reply_markup=keyboard)
