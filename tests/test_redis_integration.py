import os

import redis.asyncio as redis
import pytest

from backend.utils.redis_client import RedisClient


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_live_redis_round_trip():
    redis_url = os.environ.get("LIVE_REDIS_URL") or os.environ.get("REDIS_URL")
    if not redis_url:
        pytest.skip("No Redis URL configured")

    probe = redis.from_url(redis_url)
    try:
        await probe.ping()
    except Exception:
        pytest.skip("Live Redis instance is not reachable")
    finally:
        await probe.aclose()

    client = RedisClient()
    from backend.utils import redis_client as redis_module

    old_url = redis_module.settings.REDIS_URL
    redis_module.settings.REDIS_URL = redis_url
    try:
        await client.connect()
        await client.set_json("integration:test:key", {"value": 42}, expire=5)
        data = await client.get_json("integration:test:key")
        assert data == {"value": 42}
        await client.delete("integration:test:key")
    finally:
        await client.disconnect()
        redis_module.settings.REDIS_URL = old_url
