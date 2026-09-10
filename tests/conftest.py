import fakeredis.aioredis
import pytest

from database import Storage
from models import Trip


@pytest.fixture
async def storage():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield Storage(client)
    await client.aclose()


def make_trip(time: int = 1_700_000_000, **overrides) -> Trip:
    data = {
        "time": time,
        "phone": "+79990000000",
        "name": "Иван",
        "from_address": "ул. Ленина, 1",
        "to_address": "пр. Мира, 5",
        "distance": 12.5,
        "waiting": 3.0,
        "price": 350,
    }
    data.update(overrides)
    return Trip(**data)
