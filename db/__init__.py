import logging
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from enum import Enum
from typing import cast
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import scoped_session, sessionmaker

from config import config

logger = logging.getLogger(__name__)
_request_id_ctx_var: ContextVar[str | None] = ContextVar(
    "_request_id_ctx_var", default=None
)


def _get_session_id() -> str | None:
    return _request_id_ctx_var.get()


def _set_session_id(value: str) -> Token:
    return _request_id_ctx_var.set(value)


def _reset_session_id(token: Token):
    _request_id_ctx_var.reset(token)


class IsolationLevel(Enum):
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"

    def __str__(self):
        return self.value


class DatabaseConnector:
    def __init__(self):
        self.engine = create_engine(
            config.DATABASE_URL,
            pool_size=100,
            max_overflow=50,
            pool_timeout=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        self.session = scoped_session(
            sessionmaker(bind=self.engine),
            _get_session_id,
        )

    @contextmanager
    def session_ctx(
        self,
        isolation_level=IsolationLevel.READ_COMMITTED,
    ):
        token = _set_session_id(str(uuid4()))

        self.session.connection(
            execution_options={"isolation_level": str(isolation_level)}
        )

        err = None
        try:
            yield self.session()
        except Exception as e:
            err = e
        finally:
            self.session.remove()
            _reset_session_id(token)
            if err:
                raise err


class AsyncDatabaseConnector:
    def __init__(self):
        # 创建异步引擎
        self.engine = create_async_engine(
            config.DATABASE_URL,
            pool_size=50,
            max_overflow=50,
            pool_timeout=10,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        self.session = async_scoped_session(
            async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                autoflush=True,
                expire_on_commit=False,
            ),
            scopefunc=_get_session_id,
        )

    async def close(self):
        """
        关闭数据库引擎
        """
        await self.engine.dispose()

    @asynccontextmanager
    async def session_ctx(
        self,
        isolation_level=IsolationLevel.READ_COMMITTED,
    ):
        token = _set_session_id(str(uuid4()))

        try:
            # do nothing, only for type-hint
            self.session = cast(type[AsyncSession], self.session)

            yield self.session(
                bind=self.engine.execution_options(
                    isolation_level=str(isolation_level),
                )
            )
        finally:
            # do nothing, only for type-hint
            self.session = cast(
                async_scoped_session[AsyncSession], self.session
            )
            await self.session.remove()
            _reset_session_id(token)

    async def create_partition_table_on_postgres(
        self,
        table_name: str,
        partition_name: str,
        start: str,
        end: str,
    ):
        """
        创建分区表 (postgres)

        Args:
            table_name (str): 原表名
            partition_name (str): 分区表名
            start (str): 分区区间开始值
            end (str): 分区区间结束值
        """
        logger.info(f"try to create partition table: {partition_name}")
        async with self.session_ctx() as session:
            # 检查分区是否已存在
            check_sql = text(f"""
                SELECT 1 FROM pg_class
                WHERE relname = '{partition_name}' AND relkind = 'r'
            """)
            result = await session.execute(check_sql)

            if result.fetchone():
                logger.info(f"{partition_name} already exists.")
                return

            # 创建新的分区
            create_sql = text(f"""
                CREATE TABLE {partition_name} PARTITION OF {table_name}
                FOR VALUES FROM ('{start}') TO ('{end}');
            """)

            await session.execute(create_sql)
            await session.commit()
            logger.info(
                f"create {partition_name} for values ('{start}') TO ('{end}')"
            )


# db = DatabaseConnector()
db = AsyncDatabaseConnector()
