import asyncio

from scheduler import UpdateScheduler
from taxi import TaxiScraperError


class StubService:
    def __init__(self, results):
        self.results = list(results)

    async def update_data(self):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def make_balance_message(self):
        return "message"


class StubNotifier:
    def __init__(self):
        self.sent = []

    async def broadcast(self, text):
        self.sent.append(text)


async def test_tick_broadcasts_only_on_change():
    notifier = StubNotifier()
    scheduler = UpdateScheduler(StubService([False, True]), notifier, period=1)
    await scheduler.tick()
    assert notifier.sent == []
    await scheduler.tick()
    assert notifier.sent == ["message"]


async def test_tick_swallows_errors():
    notifier = StubNotifier()
    service = StubService([TaxiScraperError("down"), RuntimeError("bug")])
    scheduler = UpdateScheduler(service, notifier, period=1)
    await scheduler.tick()
    await scheduler.tick()
    assert notifier.sent == []


async def test_start_and_stop():
    notifier = StubNotifier()
    scheduler = UpdateScheduler(StubService([True, True, True]), notifier, period=100)
    scheduler.start()
    await asyncio.sleep(0.01)
    await scheduler.stop()
    assert notifier.sent == ["message"]
    await scheduler.stop()  # idempotent
