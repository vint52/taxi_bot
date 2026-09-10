"""Logging setup: console always, plus a file when a path is configured."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
NOISY_LOGGERS = ("aiogram", "aiohttp", "requests", "urllib3")


def setup_logging(level: str = "INFO", log_path: str | None = None) -> None:
    """Configure root logging. ``level`` is a standard logging level name."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_path:
        try:
            handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
        except OSError as exc:
            print(f"Warning: file logging disabled: {exc}", file=sys.stderr)

    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=handlers)
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
