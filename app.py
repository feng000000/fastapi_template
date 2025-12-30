import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from filelock import FileLock

from config import config
from controllers import api_router
from middlewares import RequestTimerMiddleware, SuperviseTaskMiddleware
from utils.redis_utils import redis_client

logger = logging.getLogger(__name__)

_FILELOCK = FileLock(".log.lock", timeout=0.05)


def init_logging():
    handlers: list[logging.Handler] = [
        logging.StreamHandler(stream=sys.stdout),
        logging.FileHandler(config.LOG_FILE_PATH),
    ]

    try:
        global _FILELOCK
        _FILELOCK.acquire()  # _FILELOCK.release()
        handlers.append(
            TimedRotatingFileHandler(
                config.LOG_FILE_PATH,
                when="midnight",
                interval=1,
                backupCount=14,
                encoding="utf-8",
            )
        )
    except Exception:
        pass

    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOG_LEVEL)

    for handler in handlers:

        def _converter(secs):
            tz = ZoneInfo("Asia/Shanghai")
            return datetime.fromtimestamp(secs, tz).timetuple()

        handler.formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
        )
        handler.formatter.converter = _converter
        root_logger.addHandler(handler)

    # only print log on the console
    # logging.basicConfig(
    #     level=config.LOG_LEVEL,
    #     stream=sys.stdout,
    #     format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    # )

    def init_logger(name: str, level: str = config.LOG_LEVEL):
        """specify logger's level"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

    logger.info("init_logging done.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # some init operations
    init_logging()
    yield
    await redis_client.aclose()
    # some atexit operations


def create_app():
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SuperviseTaskMiddleware)
    app.add_middleware(RequestTimerMiddleware)

    app.include_router(api_router, prefix="/api")
    app.add_api_route("healthy", endpoint=lambda: "success")

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:create_app", host="0.0.0.0", port=8000, factory=True)
