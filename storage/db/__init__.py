from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from enum import Enum
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import scoped_session, sessionmaker

from config import settings

_request_id_ctx_var: ContextVar[str | None] = ContextVar(
    "_request_id_ctx_var", default=None
)


def get_session_id() -> str | None:
    return _request_id_ctx_var.get()


def set_session_id(value: str) -> Token:
    return _request_id_ctx_var.set(value)


def reset_session_id(token: Token):
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
            settings.DATABASE_URL,
            pool_size=100,
            max_overflow=50,
            pool_timeout=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        self.session = scoped_session(
            sessionmaker(bind=self.engine),
            get_session_id,
        )

    @contextmanager
    def session_ctx(
        self,
        isolation_level=IsolationLevel.READ_COMMITTED,
    ):
        token = set_session_id(str(uuid4()))

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
            reset_session_id(token)
            if err:
                raise err


class AsyncDatabaseConnector:
    def __init__(self):
        # 创建异步引擎
        self.engine = create_async_engine(
            settings.DATABASE_URL,
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
            scopefunc=get_session_id,
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
        token = set_session_id(str(uuid4()))

        await self.session.connection(
            execution_options={"isolation_level": str(isolation_level)}
        )

        err = None
        try:
            yield self.session()
        except Exception as e:
            err = e
        finally:
            await self.session.remove()
            reset_session_id(token)
            if err:
                raise err


db = DatabaseConnector()
# db = AsyncDatabaseConnector()
