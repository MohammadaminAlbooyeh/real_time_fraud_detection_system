import json
from contextlib import asynccontextmanager
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from backend.utils.config import settings


class RedisClient:
    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    @property
    def client(self) -> Redis:
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client

    async def set_json(self, key: str, value: Any, expire: int = 3600) -> bool:
        return await self.client.set(key, json.dumps(value), ex=expire)

    async def get_json(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    # Sorted Set operations for time-window aggregations
    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        return await self.client.zadd(key, mapping)

    async def zrem(self, key: str, *members: str) -> int:
        return await self.client.zrem(key, *members)

    async def zrangebyscore(
        self, key: str, min_score: float, max_score: float, start: int = 0, num: int = -1
    ) -> list[str]:
        return await self.client.zrangebyscore(key, min_score, max_score, start=start, num=num)

    async def zcount(self, key: str, min_score: float, max_score: float) -> int:
        return await self.client.zcount(key, min_score, max_score)

    async def zsum(self, key: str, min_score: float, max_score: float) -> float:
        # Sum scores in range - useful for amount velocity
        members = await self.client.zrangebyscore(key, min_score, max_score, withscores=True)
        return sum(score for _, score in members)

    async def expire(self, key: str, seconds: int) -> bool:
        return await self.client.expire(key, seconds)

    # Hash operations for user profiles
    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        return await self.client.hset(key, mapping={k: json.dumps(v) if not isinstance(v, str) else v for k, v in mapping.items()})

    async def hget(self, key: str, field: str) -> Optional[Any]:
        value = await self.client.hget(key, field)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def hgetall(self, key: str) -> dict[str, Any]:
        data = await self.client.hgetall(key)
        result = {}
        for k, v in data.items():
            try:
                result[k] = json.loads(v)
            except json.JSONDecodeError:
                result[k] = v
        return result

    async def hdel(self, key: str, *fields: str) -> int:
        return await self.client.hdel(key, *fields)

    # Pub/Sub for real-time alerts
    async def publish(self, channel: str, message: dict[str, Any]) -> int:
        return await self.client.publish(channel, json.dumps(message))

    @asynccontextmanager
    async def pubsub(self, *channels: str):
        pubsub = self.client.pubsub()
        try:
            await pubsub.subscribe(*channels)
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # Streams for transaction processing (Kafka alternative)
    async def xadd(self, stream: str, data: dict[str, Any], maxlen: int = 10000) -> str:
        return await self.client.xadd(stream, data, maxlen=maxlen, approximate=True)

    async def xread(self, streams: dict[str, str], count: int = 100, block: int = 5000) -> list:
        return await self.client.xread(streams, count=count, block=block)

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 100,
        block: int = 5000,
    ) -> list:
        return await self.client.xreadgroup(groupname, consumername, streams, count=count, block=block)

    async def xack(self, stream: str, groupname: str, *ids: str) -> int:
        return await self.client.xack(stream, groupname, *ids)

    async def xgroup_create(self, stream: str, groupname: str, id: str = "0", mkstream: bool = True) -> bool:
        try:
            await self.client.xgroup_create(stream, groupname, id=id, mkstream=mkstream)
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                return False
            raise


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    return redis_client