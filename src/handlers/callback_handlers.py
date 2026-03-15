"""Callback query handlers."""
import logging

from aiogram.types import CallbackQuery

from config import Config
from database import RedisDatabase
from services import TaxiService
from constants import (
    MSG_USER_ACTIONS,
    MSG_USER_LOGS_HEADER,
    MSG_NO_LOGS_FOR_USER,
    MSG_LOGS_DISABLED,
    MSG_INVALID_USER_ID,
    MSG_CANNOT_DELETE_SELF_INLINE,
    MSG_USER_DELETED_INLINE,
    MSG_USER_NOT_FOUND_INLINE,
    MSG_USERS_LIST_HEADER,
    MSG_NO_USERS,
)
from utils import filter_logs_by_user, get_user_activity_summary
from .common import (
    build_back_to_users_keyboard,
    build_user_actions_keyboard,
    build_users_inline_keyboard,
)


logger = logging.getLogger(__name__)


class CallbackHandlers:
    """Callback query handlers."""
    
    def __init__(self, config: Config, db: RedisDatabase, taxi_service: TaxiService):
        """Initialize callback handlers."""
        self.config = config
        self.db = db
        self.taxi_service = taxi_service
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id == self.config.tg_admin_id
    
    async def user_callback_handler(self, callback_query: CallbackQuery) -> None:
        """Handle user selection callback."""
        if not self.is_admin(callback_query.from_user.id):
            await callback_query.answer("Доступ запрещен")
            return
        
        admin_id = callback_query.from_user.id
        admin_username = callback_query.from_user.username or "Unknown"
        data = callback_query.data or ""
        
        logger.info(f'CALLBACK_ACTION - Admin {admin_id} ({admin_username}) clicked callback: {data}')
        
        if data.startswith("user_"):
            user_id = data.replace("user_", "")
            logger.info(f'CALLBACK_ACTION - Admin {admin_id} ({admin_username}) selected user {user_id}')
            await self.show_user_actions(callback_query, user_id)
        elif data.startswith("logs_"):
            user_id = data.replace("logs_", "")
            logger.info(f'CALLBACK_ACTION - Admin {admin_id} ({admin_username}) requested logs for user {user_id}')
            await self.show_user_logs_inline(callback_query, user_id)
        elif data.startswith("delete_"):
            user_id = data.replace("delete_", "")
            logger.info(f'CALLBACK_ACTION - Admin {admin_id} ({admin_username}) requested to delete user {user_id}')
            await self.delete_user_inline(callback_query, user_id)
        elif data == "back_to_users":
            logger.info(f'CALLBACK_ACTION - Admin {admin_id} ({admin_username}) clicked "Back to users"')
            await self.show_users_inline(callback_query)
    
    async def show_user_actions(self, callback_query: CallbackQuery, user_id: str) -> None:
        """Show action buttons for selected user."""
        await callback_query.message.edit_text(
            MSG_USER_ACTIONS.format(user_id=user_id),
            reply_markup=build_user_actions_keyboard(user_id)
        )
        await callback_query.answer()
    
    async def show_user_logs_inline(self, callback_query: CallbackQuery, user_id: str) -> None:
        """Show user logs via inline button."""
        if not self.config.tg_log_path:
            await callback_query.answer(MSG_LOGS_DISABLED)
            return
        
        try:
            user_id_int = int(user_id)
        except ValueError:
            await callback_query.answer(MSG_INVALID_USER_ID)
            return
        
        # Get user activity summary
        summary = get_user_activity_summary(self.config.tg_log_path, user_id_int)
        
        if "error" in summary:
            await callback_query.answer(summary["error"])
            return
        
        # Get filtered logs
        user_logs = filter_logs_by_user(self.config.tg_log_path, user_id_int, max_lines=20)
        
        if not user_logs.strip():
            await callback_query.answer(MSG_NO_LOGS_FOR_USER.format(user_id=user_id))
            return
        
        # Create response message
        response = await self._build_inline_user_logs_response(user_id, summary, user_logs)
        
        # Split if too long
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (логи обрезаны)"
        
        await callback_query.message.edit_text(
            response,
            reply_markup=build_back_to_users_keyboard(),
        )
        await callback_query.answer()
        
        logger.info(f'User logs requested for {user_id} by admin {callback_query.from_user.id}')
    
    async def _build_inline_user_logs_response(self, user_id: str, summary: dict, user_logs: str) -> str:
        """Build inline user logs response message."""
        response = MSG_USER_LOGS_HEADER.format(user_id=user_id) + "\n\n"
        response += f"📊 Статистика: {summary['total_entries']} записей\n"
        response += f"• Запусков: {summary['activities']['start']}\n"
        response += f"• Баланс: {summary['activities']['balance']}\n"
        response += f"• Логи: {summary['activities']['logs']}\n"
        response += f"• Пользователи: {summary['activities']['users']}\n"
        response += f"• Неизвестные: {summary['activities']['unknown']}\n\n"
        
        if summary['last_activity']:
            response += f"🕐 Последняя активность:\n{summary['last_activity']}\n\n"
        
        response += "📝 Последние логи:\n"
        response += user_logs
        
        return response
    
    async def delete_user_inline(self, callback_query: CallbackQuery, user_id: str) -> None:
        """Delete user via inline button."""
        admin_id = callback_query.from_user.id
        admin_username = callback_query.from_user.username or "Unknown"
        
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.warning(f'CALLBACK_ERROR - Admin {admin_id} ({admin_username}) tried to delete invalid user ID: {user_id}')
            await callback_query.answer(MSG_INVALID_USER_ID)
            return
        
        # Check if trying to delete self
        if user_id_int == admin_id:
            logger.warning(f'CALLBACK_ERROR - Admin {admin_id} ({admin_username}) tried to delete themselves')
            await callback_query.answer(MSG_CANNOT_DELETE_SELF_INLINE.format(user_id=user_id))
            return
        
        # Remove user from database
        success = self.db.remove_user(user_id_int)
        
        if success:
            logger.info(f'USER_DELETED - User {user_id} deleted by admin {admin_id} ({admin_username})')
            await callback_query.answer(MSG_USER_DELETED_INLINE.format(user_id=user_id))
            # Show updated users list
            await self.show_users_inline(callback_query)
        else:
            logger.warning(f'CALLBACK_ERROR - Admin {admin_id} ({admin_username}) tried to delete non-existent user {user_id}')
            await callback_query.answer(MSG_USER_NOT_FOUND_INLINE.format(user_id=user_id))
    
    async def show_users_inline(self, callback_query: CallbackQuery) -> None:
        """Show users list via inline button."""
        users = self.db.get_users()
        if users:
            await self._show_users_list_inline(callback_query, users)
        else:
            await callback_query.message.edit_text(MSG_NO_USERS)
        
        await callback_query.answer()
    
    async def _show_users_list_inline(self, callback_query: CallbackQuery, users) -> None:
        """Show users list with inline keyboard."""
        await callback_query.message.edit_text(
            MSG_USERS_LIST_HEADER + "Нажмите на пользователя для управления:",
            reply_markup=build_users_inline_keyboard(users)
        )
