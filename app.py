import logging
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from controllers import api_router
from middlewares import CustomerMiddleware

logger = logging.getLogger(__name__)


def init_logging():
    api_file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
    console_handler = logging.StreamHandler()
    backup_handler = TimedRotatingFileHandler(
        settings.LOG_FILE_PATH,
        when="midnight",
        interval=1,
        backupCount=14,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        handlers=[api_file_handler, console_handler, backup_handler],
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s\n",
    )

    def init_logger(name: str, level: str = settings.LOG_LEVEL):
        """specify logger's level"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

    logger.info("init_logging done.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # some init operations
    init_logging()
    yield
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

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:create_app", host="0.0.0.0", port=8000, factory=True)
