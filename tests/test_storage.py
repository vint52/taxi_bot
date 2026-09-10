from conftest import make_trip


async def test_balance(storage):
    assert await storage.get_balance() is None
    await storage.set_balance(1500)
    assert await storage.get_balance() == 1500


async def test_users(storage):
    assert await storage.add_user(1) is True
    assert await storage.add_user(1) is False
    await storage.add_user(2)
    assert await storage.user_exists(1)
    assert not await storage.user_exists(3)
    assert await storage.get_users() == {1, 2}
    assert await storage.remove_user(1) is True
    assert await storage.remove_user(1) is False
    assert await storage.get_users() == {2}


async def test_trips_sorted_and_deduplicated(storage):
    older, newer = make_trip(time=100), make_trip(time=200)
    await storage.add_trips([newer, older])
    await storage.add_trips([older])
    assert await storage.get_recent_trips(5) == [older, newer]
    assert await storage.get_last_trip() == newer
    assert await storage.get_recent_trips(1) == [newer]


async def test_empty_trips(storage):
    await storage.add_trips([])
    assert await storage.get_recent_trips(3) == []
    assert await storage.get_last_trip() is None


async def test_timestamp(storage):
    assert await storage.get_timestamp() == 0
    await storage.set_timestamp(123)
    assert await storage.get_timestamp() == 123
    await storage.set_timestamp()
    assert await storage.get_timestamp() > 123
