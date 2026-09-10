import pytest

from logs import LogReader, LogReadError

LOG = """\
2024-01-01 10:00:00.000 INFO handlers.user: USER_START - 111 (alice) opened the bot
2024-01-01 10:00:01.000 INFO handlers.user: USER_START - 111 (alice) registered
2024-01-01 10:01:00.000 INFO handlers.user: USER_BALANCE - 111 (alice) requested balance
2024-01-01 10:02:00.000 INFO handlers.user: USER_UNKNOWN - 111 (alice) sent unknown text: 'hi'
2024-01-01 10:03:00.000 INFO handlers.user: USER_START - 222 (bob) opened the bot
2024-01-01 10:04:00.000 INFO handlers.admin: ADMIN_USERS - 1111 (root) opened the user list
2024-01-01 10:05:00.000 INFO handlers.admin: User 222 deleted by admin 1111 (root)
"""


@pytest.fixture
def reader(tmp_path):
    path = tmp_path / "tg.log"
    path.write_text(LOG, encoding="utf-8")
    return LogReader(path)


def test_tail(reader):
    lines = reader.tail(2).splitlines()
    assert len(lines) == 2
    assert "deleted by admin" in lines[-1]


def test_user_lines_match_whole_numbers(reader):
    lines = reader.user_lines(111, count=10)
    assert len(lines) == 4
    assert all("111 (alice)" in line for line in lines)
    assert reader.user_lines(111, count=2)[0].endswith("requested balance\n")


def test_user_activity(reader):
    activity = reader.user_activity(111)
    assert activity.total == 4
    assert activity.starts == 2
    assert activity.balance_checks == 1
    assert activity.unknown_commands == 1
    assert activity.user_views == 0
    assert activity.last_entry.endswith("sent unknown text: 'hi'")

    admin = reader.user_activity(1111)
    assert admin.total == 2
    assert admin.user_views == 1


def test_user_activity_unknown_user(reader):
    assert reader.user_activity(999) is None


def test_disabled_reader():
    reader = LogReader(None)
    assert not reader.enabled
    with pytest.raises(LogReadError):
        reader.tail(1)


def test_missing_file(tmp_path):
    reader = LogReader(tmp_path / "missing.log")
    assert reader.enabled
    with pytest.raises(LogReadError):
        reader.tail(1)
