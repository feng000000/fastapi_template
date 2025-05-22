from typing import Any

import aioredis
import redis

from config import config


class RedisClient:
    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        username: str,
        password: str,
    ):
        self._client = redis.Redis()
        self._client.connection_pool = redis.ConnectionPool(
            host=host,
            port=port,
            username=username,
            password=password,
            db=db,
            **{
                "encoding": "utf-8",
                "encoding_errors": "strict",
                "decode_responses": False,
            },
        )

    # TODO: update prefix
    def prefix(self):
        return "custom_prefix:"

    def get(self, key) -> Any | None:
        return self._client.get(self.prefix() + key)

    def set(self, key, value, ex=None):
        return self._client.set(self.prefix() + key, value, ex=ex)

    def delete(self, key):
        return self._client.delete(self.prefix() + key)


class AsyncRedisClient:
    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        username: str,
        password: str,
    ):
        self._client = None
        self.host = host
        self.port = port
        self.db = db
        self.username = username
        self.password = password

    async def init_client(self) -> aioredis.Redis:
        return await aioredis.from_url(
            f"redis://{self.host}:{self.port}/{self.db}",
            username=self.username,
            password=self.password,
            encoding="utf-8",
            decode_responses=False,
        )

    # TODO: update prefix
    def prefix(self):
        return "custom_prefix:"

    async def get(self, key) -> bytes | None:
        if self._client is None:
            self._client = await self.init_client()

        return await self._client.get(self.prefix() + key)

    async def set(self, key, value, ex=None) -> None:
        if self._client is None:
            self._client = await self.init_client()

        await self._client.set(self.prefix() + key, value, ex=ex)

    async def delete(self, key):
        if self._client is None:
            self._client = await self.init_client()

        return self._client.delete(self.prefix() + key)


redis_client = RedisClient(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    username=config.REDIS_USERNAME,
    password=config.REDIS_PASSWORD,
)
