"""Keyboards, filters and callback payloads shared by the routers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Filter
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    User,
)

from config import Config
from constants import (
    BTN_BACK_TO_USERS,
    BTN_CHECK_BALANCE,
    BTN_LOGS,
    BTN_USER_DELETE,
    BTN_USER_LOGS,
    BTN_USERS,
)


class AdminFilter(Filter):
    """Pass only updates coming from the configured administrator."""

    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return event.from_user is not None and event.from_user.id == config.tg_admin_id


class UserAction(CallbackData, prefix="ua"):
    """Inline button payload for the user-management screens."""

    action: Literal["show", "logs", "delete", "list"]
    user_id: int = 0


def describe(user: User) -> str:
    """Short user reference for log lines: ``123456 (username)``."""
    return f"{user.id} ({user.username or 'no username'})"


def main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    """Reply keyboard with the balance button and admin tools when applicable."""
    rows = [[KeyboardButton(text=BTN_CHECK_BALANCE)]]
    if is_admin:
        rows.insert(0, [KeyboardButton(text=BTN_LOGS), KeyboardButton(text=BTN_USERS)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def users_keyboard(user_ids: Iterable[int]) -> InlineKeyboardMarkup:
    """One button per registered user."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"👤 {user_id}",
                    callback_data=UserAction(action="show", user_id=user_id).pack(),
                )
            ]
            for user_id in sorted(user_ids)
        ]
    )


def user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Actions available for a selected user."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_USER_LOGS,
                    callback_data=UserAction(action="logs", user_id=user_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_USER_DELETE,
                    callback_data=UserAction(action="delete", user_id=user_id).pack(),
                )
            ],
            back_to_users_keyboard().inline_keyboard[0],
        ]
    )


def back_to_users_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_BACK_TO_USERS,
                    callback_data=UserAction(action="list").pack(),
                )
            ]
        ]
    )


async def edit_message(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    """Edit the message under an inline keyboard, ignoring "not modified" errors."""
    if not isinstance(query.message, Message):
        return
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
