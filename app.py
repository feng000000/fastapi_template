import atexit
import fcntl
import logging
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from controllers import api_router
from middlewares import CustomerMiddleware
from utils.redis_utils import redis_client

logger = logging.getLogger(__name__)


def init_logging():
    handler = [
        logging.FileHandler(config.LOG_FILE_PATH),
        logging.StreamHandler(),
    ]

    file_lock = open("./api.lock", "wb")
    try:
        fcntl.flock(file_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handler.append(
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

    def unlock():
        fcntl.flock(file_lock, fcntl.LOCK_UN)
        file_lock.close()

    atexit.register(unlock)

    logging.basicConfig(
        level=config.LOG_LEVEL,
        handlers=handler,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s\n",
    )

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
    app.add_middleware(CustomerMiddleware)

    app.include_router(api_router, prefix="/api")
    app.add_api_route("healthy", endpoint=lambda: "success")

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:create_app", host="0.0.0.0", port=8000, factory=True)
