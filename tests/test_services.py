from zoneinfo import ZoneInfo

import pytest

from conftest import make_trip
from models import ProfileInfo
from services import TaxiService


class FakeClient:
    def __init__(self, info: ProfileInfo):
        self.info = info
        self.calls = 0

    def get_profile_info(self):
        self.calls += 1
        return self.info


@pytest.fixture
def service(storage):
    def build(info: ProfileInfo) -> tuple[TaxiService, FakeClient]:
        client = FakeClient(info)
        return TaxiService(storage, client, ZoneInfo("Europe/Moscow")), client

    return build


async def test_first_update_stores_everything(storage, service):
    svc, client = service(ProfileInfo(balance=100, trips=[make_trip(time=10)]))
    assert await svc.update_data() is True
    assert client.calls == 1
    assert await storage.get_balance() == 100
    assert await storage.get_last_trip() == make_trip(time=10)
    assert await storage.get_timestamp() > 0


async def test_unchanged_data_reports_no_update(storage, service):
    svc, _ = service(ProfileInfo(balance=100, trips=[make_trip(time=10)]))
    await svc.update_data()
    assert await svc.update_data() is False


async def test_balance_change_only(storage, service):
    svc, _ = service(ProfileInfo(balance=100, trips=[make_trip(time=10)]))
    await svc.update_data()
    svc2, _ = service(ProfileInfo(balance=90, trips=[make_trip(time=10)]))
    assert await svc2.update_data() is True
    assert await storage.get_balance() == 90


async def test_new_trip_detected_by_last_time(storage, service):
    svc, _ = service(ProfileInfo(balance=100, trips=[make_trip(time=10)]))
    await svc.update_data()
    svc2, _ = service(ProfileInfo(balance=100, trips=[make_trip(time=10), make_trip(time=20)]))
    assert await svc2.update_data() is True
    assert [t.time for t in await storage.get_recent_trips(5)] == [10, 20]


async def test_empty_trips_never_count_as_change(storage, service):
    svc, _ = service(ProfileInfo(balance=100, trips=[]))
    await svc.update_data()
    assert await svc.update_data() is False


async def test_balance_message(storage, service):
    svc, _ = service(ProfileInfo(balance=100, trips=[make_trip(time=10, name="Пётр")]))
    await svc.update_data()
    plain = await svc.make_balance_message()
    assert "Пётр" in plain and "Последнее обновление" not in plain
    admin = await svc.make_balance_message(with_update_time=True)
    assert "Последнее обновление" in admin
