"""Entry point: wires configuration, storage, taxi client, scheduler and Telegram."""

from __future__ import annotations

import asyncio
import logging
import sys
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher

import handlers
from config import Config, ConfigError
from database import Storage
from logging_config import setup_logging
from logs import LogReader
from notifier import Notifier
from scheduler import UpdateScheduler
from services import TaxiService
from taxi import TaxiClient

logger = logging.getLogger(__name__)


async def run(config: Config) -> None:
    storage = Storage.from_config(config)
    await storage.ping()
    logger.info("Connected to Redis at %s:%s", config.redis_host, config.redis_port)

    client = TaxiClient(config.taxi_username, config.taxi_password, config.debug_html_dir)
    taxi_service = TaxiService(storage, client, ZoneInfo(config.timezone))

    bot = Bot(token=config.tg_token)
    scheduler = UpdateScheduler(taxi_service, Notifier(bot, storage), config.update_period)

    dp = Dispatcher()
    dp["config"] = config
    dp["storage"] = storage
    dp["taxi_service"] = taxi_service
    dp["log_reader"] = LogReader(config.tg_log_path)
    handlers.setup(dp)

    try:
        scheduler.start()
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        await scheduler.stop()
        await storage.close()
        await bot.session.close()
        logger.info("Bot stopped")


def main() -> None:
    try:
        config = Config.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level, config.tg_log_path)
    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("Bot crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
