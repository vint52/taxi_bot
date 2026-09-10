"""Administrator tools: log tail, user list and per-user actions."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from constants import (
    BTN_LOGS,
    BTN_USERS,
    LOG_LINES_TO_SHOW,
    MSG_CANNOT_DELETE_SELF,
    MSG_DELETE_USAGE,
    MSG_INVALID_USER_ID,
    MSG_LOGS_DISABLED,
    MSG_LOGS_EMPTY,
    MSG_LOGS_FILE_ERROR,
    MSG_NO_LOGS_FOR_USER,
    MSG_NO_USERS,
    MSG_STALE_BUTTON,
    MSG_USER_ACTIONS,
    MSG_USER_DELETED,
    MSG_USER_LOGS_USAGE,
    MSG_USER_NOT_FOUND,
    MSG_USERS_LIST,
    USER_LOG_LINES_TO_SHOW,
    USER_LOGS_TEMPLATE,
)
from database import Storage
from formatting import truncate
from logs import EVENT_ADMIN_LOGS, EVENT_ADMIN_USERS, LogReader, LogReadError

from .common import (
    AdminFilter,
    UserAction,
    back_to_users_keyboard,
    describe,
    edit_message,
    main_keyboard,
    user_actions_keyboard,
    users_keyboard,
)

logger = logging.getLogger(__name__)


def _user_logs_text(user_id: int, log_reader: LogReader) -> str:
    """Activity summary plus recent lines for ``user_id``, or a "nothing found" note."""
    activity = log_reader.user_activity(user_id)
    if activity is None:
        return MSG_NO_LOGS_FOR_USER.format(user_id=user_id)
    lines = log_reader.user_lines(user_id, USER_LOG_LINES_TO_SHOW)
    return USER_LOGS_TEMPLATE.format(
        user_id=user_id,
        total=activity.total,
        starts=activity.starts,
        balance_checks=activity.balance_checks,
        log_views=activity.log_views,
        user_views=activity.user_views,
        unknown_commands=activity.unknown_commands,
        last_entry=activity.last_entry,
        lines="".join(lines),
    )


def _parse_user_id(command: CommandObject) -> int | None:
    args = (command.args or "").split()
    if len(args) != 1:
        return None
    try:
        return int(args[0])
    except ValueError:
        return None


# --- reply keyboard --------------------------------------------------------


async def show_logs(message: Message, log_reader: LogReader) -> None:
    logger.info("%s - %s opened the log tail", EVENT_ADMIN_LOGS, describe(message.from_user))
    if not log_reader.enabled:
        text = MSG_LOGS_DISABLED
    else:
        try:
            text = log_reader.tail(LOG_LINES_TO_SHOW) or MSG_LOGS_EMPTY
        except LogReadError as exc:
            logger.error("Cannot read log file: %s", exc)
            text = MSG_LOGS_FILE_ERROR
    await message.answer(truncate(text), reply_markup=main_keyboard(is_admin=True))


async def show_users(message: Message, storage: Storage) -> None:
    logger.info("%s - %s opened the user list", EVENT_ADMIN_USERS, describe(message.from_user))
    users = await storage.get_users()
    if not users:
        await message.answer(MSG_NO_USERS, reply_markup=main_keyboard(is_admin=True))
        return
    await message.answer(MSG_USERS_LIST, reply_markup=users_keyboard(users))


# --- commands --------------------------------------------------------------


async def delete_user(message: Message, command: CommandObject, storage: Storage) -> None:
    if command.args is None:
        await message.reply(MSG_DELETE_USAGE)
        return
    user_id = _parse_user_id(command)
    if user_id is None:
        await message.reply(MSG_INVALID_USER_ID)
        return
    if user_id == message.from_user.id:
        await message.reply(MSG_CANNOT_DELETE_SELF)
        return
    if await storage.remove_user(user_id):
        logger.info("User %s deleted by admin %s", user_id, describe(message.from_user))
        await message.reply(MSG_USER_DELETED.format(user_id=user_id))
    else:
        await message.reply(MSG_USER_NOT_FOUND.format(user_id=user_id))


async def user_logs(message: Message, command: CommandObject, log_reader: LogReader) -> None:
    if command.args is None:
        await message.reply(MSG_USER_LOGS_USAGE)
        return
    user_id = _parse_user_id(command)
    if user_id is None:
        await message.reply(MSG_INVALID_USER_ID)
        return
    if not log_reader.enabled:
        await message.reply(MSG_LOGS_DISABLED)
        return
    logger.info(
        "%s - %s requested logs of user %s", EVENT_ADMIN_LOGS, describe(message.from_user), user_id
    )
    try:
        text = _user_logs_text(user_id, log_reader)
    except LogReadError as exc:
        logger.error("Cannot read log file: %s", exc)
        text = MSG_LOGS_FILE_ERROR
    await message.reply(truncate(text))


# --- inline user management -----------------------------------------------


async def _render_user_list(query: CallbackQuery, storage: Storage) -> None:
    users = await storage.get_users()
    if users:
        await edit_message(query, MSG_USERS_LIST, users_keyboard(users))
    else:
        await edit_message(query, MSG_NO_USERS, back_to_users_keyboard())


async def list_users(query: CallbackQuery, storage: Storage) -> None:
    await _render_user_list(query, storage)
    await query.answer()


async def show_user(query: CallbackQuery, callback_data: UserAction) -> None:
    user_id = callback_data.user_id
    await edit_message(
        query, MSG_USER_ACTIONS.format(user_id=user_id), user_actions_keyboard(user_id)
    )
    await query.answer()


async def show_user_logs(
    query: CallbackQuery, callback_data: UserAction, log_reader: LogReader
) -> None:
    user_id = callback_data.user_id
    logger.info(
        "%s - %s requested logs of user %s", EVENT_ADMIN_LOGS, describe(query.from_user), user_id
    )
    if not log_reader.enabled:
        await query.answer(MSG_LOGS_DISABLED)
        return
    try:
        text = _user_logs_text(user_id, log_reader)
    except LogReadError as exc:
        logger.error("Cannot read log file: %s", exc)
        await query.answer(MSG_LOGS_FILE_ERROR)
        return
    await edit_message(query, truncate(text), back_to_users_keyboard())
    await query.answer()


async def delete_user_inline(
    query: CallbackQuery, callback_data: UserAction, storage: Storage
) -> None:
    user_id = callback_data.user_id
    if user_id == query.from_user.id:
        await query.answer(MSG_CANNOT_DELETE_SELF)
        return
    if not await storage.remove_user(user_id):
        await query.answer(MSG_USER_NOT_FOUND.format(user_id=user_id))
        return
    logger.info("User %s deleted by admin %s", user_id, describe(query.from_user))
    await query.answer(MSG_USER_DELETED.format(user_id=user_id))
    await _render_user_list(query, storage)


async def stale_button(query: CallbackQuery) -> None:
    """Buttons from messages sent by an older bot version."""
    await query.answer(MSG_STALE_BUTTON)


def create_router() -> Router:
    """Administrator handlers; every update here must pass :class:`AdminFilter`."""
    router = Router(name="admin")
    router.message.filter(AdminFilter())
    router.callback_query.filter(AdminFilter())

    router.message.register(show_logs, F.text == BTN_LOGS)
    router.message.register(show_users, F.text == BTN_USERS)
    router.message.register(delete_user, Command("delete"))
    router.message.register(user_logs, Command("logs"))

    router.callback_query.register(list_users, UserAction.filter(F.action == "list"))
    router.callback_query.register(show_user, UserAction.filter(F.action == "show"))
    router.callback_query.register(show_user_logs, UserAction.filter(F.action == "logs"))
    router.callback_query.register(delete_user_inline, UserAction.filter(F.action == "delete"))
    router.callback_query.register(stale_button)
    return router
