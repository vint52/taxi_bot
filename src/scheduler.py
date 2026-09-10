"""Periodic polling of the taxi cabinet."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from notifier import Notifier
from services import TaxiService
from taxi import TaxiError

logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Runs ``TaxiService.update_data`` every ``period`` seconds and notifies on changes."""

    def __init__(self, service: TaxiService, notifier: Notifier, period: int) -> None:
        self._service = service
        self._notifier = notifier
        self._period = period
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="taxi-updates")
        logger.info("Update scheduler started, period %ds", self._period)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Update scheduler stopped")

    async def _run(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(self._period)

    async def tick(self) -> None:
        """One polling cycle; never raises so the loop keeps going."""
        try:
            changed = await self._service.update_data()
        except TaxiError as exc:
            logger.error("Cabinet update failed: %s", exc)
            return
        except Exception:
            logger.exception("Unexpected error during cabinet update")
            return

        if not changed:
            logger.debug("No changes in the cabinet")
            return
        try:
            await self._notifier.broadcast(await self._service.make_balance_message())
        except Exception:
            logger.exception("Failed to broadcast the update")
