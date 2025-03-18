from typing import Any

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
        self.redis_client = redis.Redis()
        self.redis_client.connection_pool = redis.ConnectionPool(
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

    def prefix(self):
        return "pdf_reader_demo:black_list:"

    def get(self, key) -> Any | None:
        return self.redis_client.get(self.prefix() + key)

    def set(self, key, value, ex=None):
        return self.redis_client.set(self.prefix() + key, value, ex=ex)

    def delete(self, key):
        return self.redis_client.delete(self.prefix() + key)


redis_client = RedisClient(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    username=config.REDIS_USERNAME,
    password=config.REDIS_PASSWORD,
)
