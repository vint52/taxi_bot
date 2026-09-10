"""Telegram update handlers."""

from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.types import ErrorEvent

from constants import MSG_INTERNAL_ERROR

from . import admin, user

logger = logging.getLogger(__name__)


async def _on_error(event: ErrorEvent) -> None:
    """Log unhandled handler exceptions and tell the user something went wrong."""
    logger.exception("Unhandled error while processing update: %s", event.exception)
    if event.update.message is not None:
        await event.update.message.answer(MSG_INTERNAL_ERROR)
    elif event.update.callback_query is not None:
        await event.update.callback_query.answer(MSG_INTERNAL_ERROR)


def setup(dp: Dispatcher) -> None:
    """Attach routers and the error handler. Admin router goes first so its filters apply."""
    dp.include_routers(admin.create_router(), user.create_router())
    dp.errors.register(_on_error)


__all__ = ["setup"]
