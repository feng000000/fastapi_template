from typing import Any
from typing import cast
# import redis
from redis import asyncio as aioredis

from config import config


# class RedisClient:
#     def __init__(
#         self,
#         prefix: str,
#         host: str,
#         port: int,
#         db: int,
#         username: str,
#         password: str,
#     ):
#         self._client = redis.Redis()
#         if not prefix.endswith(":"):
#             self.prefix = prefix + ":"
#         else:
#             self.prefix = prefix

#         self._client.connection_pool = redis.ConnectionPool(
#             host=host,
#             port=port,
#             username=username,
#             password=password,
#             db=db,
#             **{
#                 "encoding": "utf-8",
#                 "encoding_errors": "strict",
#                 "decode_responses": False,
#             },
#         )

#     def get(self, key) -> Any | None:
#         return self._client.get(self.prefix + key)

#     def set(self, key, value, ex=None):
#         return self._client.set(self.prefix + key, value, ex=ex)

#     def delete(self, key):
#         return self._client.delete(self.prefix + key)



class AsyncRedisClient:
    def __init__(
        self,
        prefix: str,
        host: str,
        port: int,
        db: int,
        username: str,
        password: str,
    ):
        if not prefix.endswith(":"):
            self.prefix = prefix + ":"
        else:
            self.prefix = prefix

        self._client: aioredis.Redis | None = None
        self.host = host
        self.port = port
        self.db = db
        self.username = username
        self.password = password

    async def init_client(self) -> aioredis.Redis:
        """创建异步 Redis 客户端。

        Returns:
            配置为返回原始字节的 Redis 客户端。
        """
        return await aioredis.from_url(
            f"redis://{self.host}:{self.port}/{self.db}",
            username=self.username,
            password=self.password,
            encoding="utf-8",
            decode_responses=False,
        )

    async def _get_client(self) -> aioredis.Redis:
        """获取已经初始化的 Redis 客户端。

        Returns:
            已存在的客户端，或者新初始化的客户端。
        """
        if self._client is None:
            self._client = await self.init_client()
        return self._client

    async def aclose(self) -> None:
        """关闭 Redis 连接池。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> bytes | None:
        """获取字符串类型的值。

        Args:
            key: 不包含公共前缀的 Redis 键。

        Returns:
            原始字节值；键不存在时返回 ``None``。
        """
        client = await self._get_client()
        return cast(bytes | None, await client.get(self.prefix + key))

    async def set(self, key: str, value: str) -> bool:
        """设置字符串类型的值。

        Args:
            key: 不包含公共前缀的 Redis 键。
            value: 要存储的值。

        Returns:
            操作成功时返回 ``True``。
        """
        client = await self._get_client()
        return bool(await client.set(self.prefix + key, value))

    async def expire(self, key: str, seconds: int) -> bool:
        """设置 Redis 键的过期时间。

        Args:
            key: 不包含公共前缀的 Redis 键。
            seconds: 过期时间，单位为秒。

        Returns:
            成功设置过期时间时返回 ``True``；键不存在时返回 ``False``。
        """
        client = await self._get_client()
        return bool(await client.expire(self.prefix + key, seconds))

    async def delete(self, key: str) -> int:
        """删除任意 Redis 数据类型的键。

        Args:
            key: 不包含公共前缀的 Redis 键。

        Returns:
            成功删除的键数量。
        """
        client = await self._get_client()
        return await client.delete(self.prefix + key)

    async def hset(
        self,
        key: str,
        mapping: dict[str, str],
    ) -> int:
        """设置哈希表中的一个或多个字段。

        Args:
            key: 不包含公共前缀的哈希表键。
            mapping: 要存储的字段和值映射。

        Returns:
            新增到哈希表的字段数量。
        """
        client = await self._get_client()
        return await client.hset(
            self.prefix + key,
            mapping=cast(Any, mapping),
        )

    async def hget(self, key: str, field: str) -> bytes | None:
        """获取哈希表中的字段值。

        Args:
            key: 不包含公共前缀的哈希表键。
            field: 要获取的哈希表字段。

        Returns:
            字段的原始字节值；字段不存在时返回 ``None``。
        """
        client = await self._get_client()
        return cast(bytes | None, await client.hget(self.prefix + key, field))

    async def hgetall(self, key: str) -> dict[bytes, bytes]:
        """获取哈希表中的所有字段和值。

        Args:
            key: 不包含公共前缀的哈希表键。

        Returns:
            包含原始字节字段名和值的映射。
        """
        client = await self._get_client()
        return cast(dict[bytes, bytes], await client.hgetall(self.prefix + key))

    async def hdel(self, key: str, *fields: str) -> int:
        """删除哈希表中的字段。

        Args:
            key: 不包含公共前缀的哈希表键。
            *fields: 要删除的字段。

        Returns:
            从哈希表中成功删除的字段数量。
        """
        client = await self._get_client()
        return await client.hdel(self.prefix + key, *fields)

    async def lpush(self, key: str, *values: str) -> int:
        """向列表头部插入一个或多个值。

        Args:
            key: 不包含公共前缀的列表键。
            *values: 要插入列表头部的值。

        Returns:
            操作完成后的列表长度。
        """
        client = await self._get_client()
        return await client.lpush(self.prefix + key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        """向列表尾部追加一个或多个值。

        Args:
            key: 不包含公共前缀的列表键。
            *values: 要追加到列表尾部的值。

        Returns:
            操作完成后的列表长度。
        """
        client = await self._get_client()
        return await client.rpush(self.prefix + key, *values)

    async def lpop(self, key: str) -> bytes | None:
        """删除并返回列表中的第一个值。

        Args:
            key: 不包含公共前缀的列表键。

        Returns:
            删除的原始字节值；列表为空时返回 ``None``。
        """
        client = await self._get_client()
        return cast(bytes | None, await client.lpop(self.prefix + key))

    async def rpop(self, key: str) -> bytes | None:
        """删除并返回列表中的最后一个值。

        Args:
            key: 不包含公共前缀的列表键。

        Returns:
            删除的原始字节值；列表为空时返回 ``None``。
        """
        client = await self._get_client()
        return cast(bytes | None, await client.rpop(self.prefix + key))

    async def lrange(self, key: str, start: int, end: int) -> list[bytes]:
        """获取列表指定索引范围内的值。

        Args:
            key: 不包含公共前缀的列表键。
            start: 起始索引，包含该位置。
            end: 结束索引，包含该位置；使用 ``-1`` 表示最后一个值。

        Returns:
            指定范围内的原始字节值列表。
        """
        client = await self._get_client()
        return cast(list[bytes], await client.lrange(self.prefix + key, start, end))

    async def sadd(self, key: str, *members: str) -> int:
        """向集合添加一个或多个成员。

        Args:
            key: 不包含公共前缀的集合键。
            *members: 要添加的成员。

        Returns:
            新增到集合中的成员数量。
        """
        client = await self._get_client()
        return await client.sadd(self.prefix + key, *members)

    async def srem(self, key: str, *members: str) -> int:
        """从集合中删除一个或多个成员。

        Args:
            key: 不包含公共前缀的集合键。
            *members: 要删除的成员。

        Returns:
            从集合中成功删除的成员数量。
        """
        client = await self._get_client()
        return await client.srem(self.prefix + key, *members)

    async def smembers(self, key: str) -> builtins.set[bytes]:
        """获取集合中的所有成员。

        Args:
            key: 不包含公共前缀的集合键。

        Returns:
            集合中的所有原始字节成员。
        """
        client = await self._get_client()
        return cast(
            builtins.set[bytes],
            await client.smembers(self.prefix + key),
        )

    async def sismember(self, key: str, member: str) -> bool:
        """检查指定值是否为集合成员。

        Args:
            key: 不包含公共前缀的集合键。
            member: 要检查的成员。

        Returns:
            成员存在于集合中时返回 ``True``。
        """
        client = await self._get_client()
        return bool(await client.sismember(self.prefix + key, member))

    async def zadd(
        self,
        key: str,
        mapping: dict[str, float],
    ) -> int:
        """向有序集合添加带分数的成员。

        Args:
            key: 不包含公共前缀的有序集合键。
            mapping: 要新增或更新的成员与分数映射。

        Returns:
            新增到有序集合中的成员数量。
        """
        client = await self._get_client()
        return cast(
            int,
            await client.zadd(
                self.prefix + key,
                cast(Any, mapping),
            ),
        )

    async def zrem(self, key: str, *members: str) -> int:
        """从有序集合中删除成员。

        Args:
            key: 不包含公共前缀的有序集合键。
            *members: 要删除的成员。

        Returns:
            从有序集合中成功删除的成员数量。
        """
        client = await self._get_client()
        return await client.zrem(self.prefix + key, *members)

    async def zrange(self, key: str, start: int, end: int) -> list[bytes]:
        """按照排名范围获取有序集合成员。

        Args:
            key: 不包含公共前缀的有序集合键。
            start: 起始排名，包含该位置。
            end: 结束排名，包含该位置；使用 ``-1`` 表示最后一个成员。

        Returns:
            按分数升序排列的原始字节成员。
        """
        client = await self._get_client()
        return cast(list[bytes], await client.zrange(self.prefix + key, start, end))

    async def zrangebyscore(
        self,
        key: str,
        minimum: int | float | str,
        maximum: int | float | str,
    ) -> list[bytes]:
        """获取分数处于指定范围内的有序集合成员。

        Args:
            key: 不包含公共前缀的有序集合键。
            minimum: 最小分数，支持 ``-inf`` 等 Redis 特殊值。
            maximum: 最大分数，支持 ``+inf`` 等 Redis 特殊值。

        Returns:
            按分数升序排列的原始字节成员。
        """
        client = await self._get_client()
        return cast(
            list[bytes],
            await client.zrangebyscore(self.prefix + key, minimum, maximum),
        )

    async def zscore(self, key: str, member: str) -> float | None:
        """获取有序集合成员的分数。

        Args:
            key: 不包含公共前缀的有序集合键。
            member: 要获取分数的成员。

        Returns:
            成员的分数；成员不存在时返回 ``None``。
        """
        client = await self._get_client()
        score = await client.zscore(self.prefix + key, member)
        return None if score is None else float(score)


# redis_client = RedisClient(
redis_client = AsyncRedisClient(
    # TODO: update prefix
    prefix="custom-prefix:",
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    username=config.REDIS_USERNAME,
    password=config.REDIS_PASSWORD,
)
