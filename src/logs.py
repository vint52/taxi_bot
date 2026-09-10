"""Reading the application log file back for the administrator."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

# Markers written by the handlers; the activity summary counts them per user.
EVENT_START = "USER_START"
EVENT_BALANCE = "USER_BALANCE"
EVENT_UNKNOWN = "USER_UNKNOWN"
EVENT_ADMIN_LOGS = "ADMIN_LOGS"
EVENT_ADMIN_USERS = "ADMIN_USERS"


class LogReadError(Exception):
    """The log file could not be read."""


@dataclass(frozen=True, slots=True)
class UserActivity:
    """Per-user counters derived from log lines mentioning the user."""

    total: int
    starts: int
    balance_checks: int
    log_views: int
    user_views: int
    unknown_commands: int
    last_entry: str


class LogReader:
    """Tail and filter the log file the bot itself writes to."""

    def __init__(self, path: str | Path | None) -> None:
        self._path = Path(path) if path else None

    @property
    def enabled(self) -> bool:
        return self._path is not None

    def tail(self, count: int) -> str:
        """Return the last ``count`` lines of the log."""
        return "".join(deque(self._iter_lines(), maxlen=count))

    def user_lines(self, user_id: int, count: int) -> list[str]:
        """Return the last ``count`` lines that mention ``user_id`` as a whole number."""
        pattern = re.compile(rf"\b{user_id}\b")
        return list(
            deque((line for line in self._iter_lines() if pattern.search(line)), maxlen=count)
        )

    def user_activity(self, user_id: int) -> UserActivity | None:
        """Summarise what ``user_id`` did; None if the log never mentions them."""
        pattern = re.compile(rf"\b{user_id}\b")
        counters = dict.fromkeys(
            (EVENT_START, EVENT_BALANCE, EVENT_ADMIN_LOGS, EVENT_ADMIN_USERS, EVENT_UNKNOWN), 0
        )
        total = 0
        last_entry = ""
        for line in self._iter_lines():
            if not pattern.search(line):
                continue
            total += 1
            last_entry = line.rstrip()
            for event in counters:
                if event in line:
                    counters[event] += 1
                    break
        if not total:
            return None
        return UserActivity(
            total=total,
            starts=counters[EVENT_START],
            balance_checks=counters[EVENT_BALANCE],
            log_views=counters[EVENT_ADMIN_LOGS],
            user_views=counters[EVENT_ADMIN_USERS],
            unknown_commands=counters[EVENT_UNKNOWN],
            last_entry=last_entry,
        )

    def _iter_lines(self):
        if self._path is None:
            raise LogReadError("Log file is not configured")
        try:
            with self._path.open(encoding="utf-8", errors="replace") as handle:
                yield from handle
        except OSError as exc:
            raise LogReadError(str(exc)) from exc
