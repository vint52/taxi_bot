"""Shared helpers for bot handlers."""

from collections.abc import Iterable

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from constants import (
    BTN_BACK_TO_USERS,
    BTN_CHECK_BALANCE,
    BTN_LOGS,
    BTN_USER_DELETE,
    BTN_USER_LOGS,
    BTN_USERS,
)


def build_main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    """Build the main reply keyboard for a user."""
    keyboard_rows = [[KeyboardButton(text=BTN_CHECK_BALANCE)]]
    if is_admin:
        keyboard_rows.insert(
            0,
            [
                KeyboardButton(text=BTN_LOGS),
                KeyboardButton(text=BTN_USERS),
            ],
        )

    return ReplyKeyboardMarkup(keyboard=keyboard_rows, resize_keyboard=True)


def build_users_inline_keyboard(user_ids: Iterable[str]) -> InlineKeyboardMarkup:
    """Build an inline keyboard with one button per user."""
    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=f"👤 {user_id}",
                callback_data=f"user_{user_id}",
            )
        ]
        for user_id in sorted(str(user_id) for user_id in user_ids)
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def build_user_actions_keyboard(user_id: str) -> InlineKeyboardMarkup:
    """Build action buttons for a selected user."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_USER_LOGS, callback_data=f"logs_{user_id}")],
            [InlineKeyboardButton(text=BTN_USER_DELETE, callback_data=f"delete_{user_id}")],
            [InlineKeyboardButton(text=BTN_BACK_TO_USERS, callback_data="back_to_users")],
        ]
    )


def build_back_to_users_keyboard() -> InlineKeyboardMarkup:
    """Build a keyboard with a single back button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_BACK_TO_USERS, callback_data="back_to_users")]
        ]
    )
