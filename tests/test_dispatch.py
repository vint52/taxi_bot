"""End-to-end routing checks: real Dispatcher, recorded outgoing API calls."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User

import handlers
from config import Config
from conftest import make_trip
from constants import (
    BTN_CHECK_BALANCE,
    BTN_USERS,
    MSG_ACCESS_DENIED,
    MSG_COMMAND_NOT_FOUND,
    MSG_PRIVATE_BOT,
    MSG_SECRET_CODE_ACCEPTED,
    MSG_STALE_BUTTON,
    MSG_USER_DELETED,
    MSG_USERS_LIST,
    MSG_WELCOME,
)
from handlers.common import UserAction
from logs import LogReader
from models import ProfileInfo
from services import TaxiService

ADMIN_ID = 1000
USER_ID = 2000


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        return True

    async def stream_content(self, *args, **kwargs):
        yield b""


class FakeClient:
    def get_profile_info(self):
        return ProfileInfo(balance=500, trips=[make_trip()])


def make_config(**overrides) -> Config:
    return Config(
        tg_token="42:TEST",
        tg_admin_id=ADMIN_ID,
        redis_host="x",
        redis_password="x",
        taxi_username="x",
        taxi_password="x",
        **overrides,
    )


@pytest.fixture
def session():
    return RecordingSession()


@pytest.fixture
def bot(session):
    return Bot(token="42:TEST", session=session)


@pytest.fixture
def make_dp(storage, tmp_path):
    def build(config: Config) -> Dispatcher:
        dp = Dispatcher()
        dp["config"] = config
        dp["storage"] = storage
        dp["taxi_service"] = TaxiService(storage, FakeClient(), ZoneInfo("Europe/Moscow"))
        dp["log_reader"] = LogReader(tmp_path / "tg.log")
        handlers.setup(dp)
        return dp

    return build


_counter = iter(range(1, 10_000))


def message_update(user_id: int, text: str) -> Update:
    user = User(id=user_id, is_bot=False, first_name="T", username=f"u{user_id}")
    chat = Chat(id=user_id, type="private")
    message = Message(
        message_id=next(_counter), date=datetime.now(), chat=chat, from_user=user, text=text
    )
    return Update(update_id=next(_counter), message=message)


def callback_update(user_id: int, data: str) -> Update:
    user = User(id=user_id, is_bot=False, first_name="T")
    chat = Chat(id=user_id, type="private")
    message = Message(message_id=next(_counter), date=datetime.now(), chat=chat, text="list")
    query = CallbackQuery(
        id=str(next(_counter)), from_user=user, chat_instance="ci", message=message, data=data
    )
    return Update(update_id=next(_counter), callback_query=query)


def sent_texts(session: RecordingSession) -> list[str]:
    return [call.text for call in session.calls if isinstance(call, SendMessage)]


async def test_public_start_registers_user(bot, session, storage, make_dp):
    dp = make_dp(make_config())
    await dp.feed_update(bot, message_update(USER_ID, "/start"))
    assert sent_texts(session) == [MSG_WELCOME]
    assert await storage.user_exists(USER_ID)
    keyboard = session.calls[0].reply_markup.keyboard
    assert [[b.text for b in row] for row in keyboard] == [[BTN_CHECK_BALANCE]]


async def test_admin_start_gets_admin_keyboard(bot, session, make_dp):
    dp = make_dp(make_config())
    await dp.feed_update(bot, message_update(ADMIN_ID, "/start"))
    keyboard = session.calls[0].reply_markup.keyboard
    assert len(keyboard) == 2


async def test_private_mode_flow(bot, session, storage, make_dp):
    dp = make_dp(make_config(bot_secret_code="open sesame"))
    await dp.feed_update(bot, message_update(USER_ID, "/start"))
    assert sent_texts(session) == [MSG_PRIVATE_BOT]

    await dp.feed_update(bot, message_update(USER_ID, "wrong"))
    assert sent_texts(session) == [MSG_PRIVATE_BOT]  # silent on a wrong code

    await dp.feed_update(bot, message_update(USER_ID, BTN_CHECK_BALANCE))
    assert sent_texts(session) == [MSG_PRIVATE_BOT, MSG_PRIVATE_BOT]

    await dp.feed_update(bot, message_update(USER_ID, "open sesame"))
    assert sent_texts(session)[-2:] == [MSG_SECRET_CODE_ACCEPTED, MSG_WELCOME]
    assert await storage.user_exists(USER_ID)

    await dp.feed_update(bot, message_update(USER_ID, BTN_CHECK_BALANCE))
    assert "Баланс" in sent_texts(session)[-1]


async def test_private_mode_admin_is_exempt(bot, session, storage, make_dp):
    dp = make_dp(make_config(bot_secret_code="open sesame"))
    await dp.feed_update(bot, message_update(ADMIN_ID, "/start"))
    assert sent_texts(session) == [MSG_WELCOME]
    assert await storage.user_exists(ADMIN_ID)


async def test_balance_for_user_and_admin(bot, session, storage, make_dp):
    dp = make_dp(make_config())
    await dp["taxi_service"].update_data()
    await dp.feed_update(bot, message_update(USER_ID, BTN_CHECK_BALANCE))
    await dp.feed_update(bot, message_update(ADMIN_ID, BTN_CHECK_BALANCE))
    user_text, admin_text = sent_texts(session)
    assert "500 р." in user_text and "Последнее обновление" not in user_text
    assert "Последнее обновление" in admin_text
    assert session.calls[0].parse_mode == "HTML"
    assert await storage.user_exists(USER_ID)


async def test_admin_buttons_hidden_from_users(bot, session, make_dp):
    dp = make_dp(make_config())
    await dp.feed_update(bot, message_update(USER_ID, BTN_USERS))
    assert sent_texts(session) == [MSG_COMMAND_NOT_FOUND]


async def test_admin_user_list_and_callbacks(bot, session, storage, make_dp):
    dp = make_dp(make_config())
    await storage.add_user(USER_ID)
    await dp.feed_update(bot, message_update(ADMIN_ID, BTN_USERS))
    assert sent_texts(session) == [MSG_USERS_LIST]
    button = session.calls[0].reply_markup.inline_keyboard[0][0]
    assert UserAction.unpack(button.callback_data).user_id == USER_ID

    await dp.feed_update(bot, callback_update(ADMIN_ID, button.callback_data))
    edits = [c for c in session.calls if isinstance(c, EditMessageText)]
    assert f"Пользователь {USER_ID}" in edits[-1].text

    delete = UserAction(action="delete", user_id=USER_ID).pack()
    await dp.feed_update(bot, callback_update(ADMIN_ID, delete))
    answers = [c for c in session.calls if isinstance(c, AnswerCallbackQuery)]
    assert answers[-1].text == MSG_USER_DELETED.format(user_id=USER_ID)
    assert not await storage.user_exists(USER_ID)


async def test_callbacks_denied_for_users_and_stale_for_admin(bot, session, make_dp):
    dp = make_dp(make_config())
    await dp.feed_update(bot, callback_update(USER_ID, UserAction(action="list").pack()))
    await dp.feed_update(bot, callback_update(ADMIN_ID, "user_123"))
    answers = [c.text for c in session.calls if isinstance(c, AnswerCallbackQuery)]
    assert answers == [MSG_ACCESS_DENIED, MSG_STALE_BUTTON]


async def test_delete_command(bot, session, storage, make_dp):
    dp = make_dp(make_config())
    await storage.add_user(USER_ID)
    await dp.feed_update(bot, message_update(USER_ID, f"/delete {ADMIN_ID}"))
    assert sent_texts(session) == [MSG_COMMAND_NOT_FOUND]
    await dp.feed_update(bot, message_update(ADMIN_ID, f"/delete {USER_ID}"))
    assert sent_texts(session)[-1] == MSG_USER_DELETED.format(user_id=USER_ID)
    assert not await storage.user_exists(USER_ID)


async def test_non_text_message_gets_not_found(bot, session, make_dp):
    dp = make_dp(make_config())
    user = User(id=USER_ID, is_bot=False, first_name="T")
    chat = Chat(id=USER_ID, type="private")
    message = Message(
        message_id=next(_counter), date=datetime.now(), chat=chat, from_user=user, sticker=None
    )
    await dp.feed_update(bot, Update(update_id=next(_counter), message=message))
    assert sent_texts(session) == [MSG_COMMAND_NOT_FOUND]
