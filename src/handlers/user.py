"""Handlers available to every user: registration, secret code, balance."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from constants import (
    BTN_CHECK_BALANCE,
    MSG_ACCESS_DENIED,
    MSG_COMMAND_NOT_FOUND,
    MSG_PRIVATE_BOT,
    MSG_SECRET_CODE_ACCEPTED,
    MSG_WELCOME,
)
from database import Storage
from logs import EVENT_BALANCE, EVENT_START, EVENT_UNKNOWN
from services import TaxiService

from .common import describe, main_keyboard

logger = logging.getLogger(__name__)


def _is_admin(message: Message, config: Config) -> bool:
    return message.from_user is not None and message.from_user.id == config.tg_admin_id


async def _has_access(message: Message, config: Config, storage: Storage) -> bool:
    """Whether the sender may see cabinet data; registers them in public mode."""
    user_id = message.from_user.id
    if _is_admin(message, config):
        return True
    if await storage.user_exists(user_id):
        return True
    if config.is_private:
        return False
    await storage.add_user(user_id)
    return True


async def start(message: Message, config: Config, storage: Storage) -> None:
    user = message.from_user
    is_admin = _is_admin(message, config)
    logger.info("%s - %s opened the bot", EVENT_START, describe(user))

    if config.is_private and not is_admin and not await storage.user_exists(user.id):
        logger.info("%s - %s must enter the secret code", EVENT_START, describe(user))
        await message.answer(MSG_PRIVATE_BOT)
        return

    if await storage.add_user(user.id):
        logger.info("%s - %s registered", EVENT_START, describe(user))
    await message.answer(MSG_WELCOME, reply_markup=main_keyboard(is_admin))


async def balance(
    message: Message, config: Config, storage: Storage, taxi_service: TaxiService
) -> None:
    user = message.from_user
    if not await _has_access(message, config, storage):
        logger.info("%s - %s asked for balance without access", EVENT_BALANCE, describe(user))
        await message.answer(MSG_PRIVATE_BOT)
        return

    is_admin = _is_admin(message, config)
    logger.info("%s - %s requested balance", EVENT_BALANCE, describe(user))
    text = await taxi_service.make_balance_message(with_update_time=is_admin)
    await message.answer(text, reply_markup=main_keyboard(is_admin), parse_mode=ParseMode.HTML)


async def fallback(message: Message, config: Config, storage: Storage) -> None:
    """Anything else: either a secret-code attempt or an unsupported command."""
    user = message.from_user
    text = message.text or ""
    if config.is_private and not await _has_access(message, config, storage):
        if text.strip() == config.bot_secret_code:
            await storage.add_user(user.id)
            logger.info("%s - %s registered with the secret code", EVENT_START, describe(user))
            keyboard = main_keyboard(is_admin=False)
            await message.answer(MSG_SECRET_CODE_ACCEPTED, reply_markup=keyboard)
            await message.answer(MSG_WELCOME, reply_markup=keyboard)
        else:
            logger.info("%s - %s sent a wrong secret code", EVENT_UNKNOWN, describe(user))
        return

    logger.info("%s - %s sent unknown input: %r", EVENT_UNKNOWN, describe(user), text)
    await message.reply(
        MSG_COMMAND_NOT_FOUND, reply_markup=main_keyboard(_is_admin(message, config))
    )


async def denied(query: CallbackQuery) -> None:
    """Inline buttons are admin-only; anyone else gets a polite refusal."""
    await query.answer(MSG_ACCESS_DENIED)


def create_router() -> Router:
    """Handlers for everyone; the text fallback and callback refusal go last."""
    router = Router(name="user")
    router.message.filter(F.from_user)
    router.message.register(start, CommandStart())
    router.message.register(start, Command("help"))
    router.message.register(balance, F.text == BTN_CHECK_BALANCE)
    router.message.register(fallback)
    router.callback_query.register(denied)
    return router
