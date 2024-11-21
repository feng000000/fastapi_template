from contextlib import contextmanager
from contextvars import ContextVar, Token
from uuid import uuid4

from sqlalchemy import create_engine
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

        factory = sessionmaker(bind=self.engine)
        self.session = scoped_session(factory, get_session_id)

    @contextmanager
    def session_ctx(self):
        token = set_session_id(uuid4().hex)

        yield self.session

        self.session.remove()
        reset_session_id(token)


db = DatabaseConnector()
