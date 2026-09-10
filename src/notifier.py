"""Broadcasting messages to every registered user."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from database import Storage

logger = logging.getLogger(__name__)


class Notifier:
    """Sends the same HTML message to all registered users, one failure at a time."""

    def __init__(self, bot: Bot, storage: Storage) -> None:
        self._bot = bot
        self._storage = storage

    async def broadcast(self, text: str) -> None:
        users = await self._storage.get_users()
        logger.info("Broadcasting update to %d users", len(users))
        for user_id in sorted(users):
            try:
                await self._bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
            except TelegramForbiddenError:
                logger.warning("User %s has blocked the bot", user_id)
            except TelegramAPIError as exc:
                logger.error("Failed to notify user %s: %s", user_id, exc)
