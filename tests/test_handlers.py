from aiogram.filters import CommandObject
from aiogram.types import InlineKeyboardMarkup

from constants import BTN_CHECK_BALANCE, BTN_LOGS, BTN_USERS, MSG_NO_LOGS_FOR_USER
from handlers.admin import _parse_user_id, _user_logs_text
from handlers.common import UserAction, main_keyboard, user_actions_keyboard, users_keyboard
from logs import LogReader


def test_main_keyboard():
    user_rows = [[b.text for b in row] for row in main_keyboard(is_admin=False).keyboard]
    assert user_rows == [[BTN_CHECK_BALANCE]]
    admin_rows = [[b.text for b in row] for row in main_keyboard(is_admin=True).keyboard]
    assert admin_rows == [[BTN_LOGS, BTN_USERS], [BTN_CHECK_BALANCE]]


def test_users_keyboard_sorted_with_callbacks():
    markup = users_keyboard({30, 10, 20})
    assert isinstance(markup, InlineKeyboardMarkup)
    payloads = [UserAction.unpack(row[0].callback_data) for row in markup.inline_keyboard]
    assert [p.user_id for p in payloads] == [10, 20, 30]
    assert all(p.action == "show" for p in payloads)


def test_user_actions_keyboard():
    markup = user_actions_keyboard(7)
    actions = [UserAction.unpack(row[0].callback_data).action for row in markup.inline_keyboard]
    assert actions == ["logs", "delete", "list"]


def test_parse_user_id():
    assert _parse_user_id(CommandObject(prefix="/", command="delete", args="123")) == 123
    assert _parse_user_id(CommandObject(prefix="/", command="delete", args="abc")) is None
    assert _parse_user_id(CommandObject(prefix="/", command="delete", args="1 2")) is None
    assert _parse_user_id(CommandObject(prefix="/", command="delete", args=None)) is None


def test_user_logs_text(tmp_path):
    path = tmp_path / "tg.log"
    path.write_text(
        "2024-01-01 10:00:00.000 INFO x: USER_START - 5 (a) opened the bot\n"
        "2024-01-01 10:01:00.000 INFO x: USER_BALANCE - 5 (a) requested balance\n",
        encoding="utf-8",
    )
    text = _user_logs_text(5, LogReader(path))
    assert "Логи для пользователя 5" in text
    assert "Статистика: 2 записей" in text
    assert "Запусков бота: 1" in text
    assert "Проверок баланса: 1" in text
    assert text.rstrip().endswith("requested balance")
    assert _user_logs_text(6, LogReader(path)) == MSG_NO_LOGS_FOR_USER.format(user_id=6)
