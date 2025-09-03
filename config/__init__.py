import os
from functools import cached_property
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _BasicConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file="./docker/.env")


class ProjectConfig(_BasicConfig):
    # TODO: update ProjectSettings
    LOG_FILE_PATH: str
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    SECRET_KEY: str

    @field_validator("LOG_FILE_PATH")
    @classmethod
    def validate_log_file_path(cls, value: Any):
        log_dir = os.path.dirname(value)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return value

    @cached_property
    def SOME_CONFIG(self) -> dict:  # noqa: N802
        config = {}
        # TODO: parse config
        return config


class DatabaseConfig(_BasicConfig):
    DB_HOST: str
    DB_PORT: str
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_DATABASE: str

    @cached_property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return (
            "postgresql://"
            f"{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}"
            f"/{self.DB_DATABASE}"
        )
        # async database url
        # return (
        #     "postgresql+asyncpg://"
        #     f"{self.DB_USERNAME}:{self.DB_PASSWORD}"
        #     f"@{self.DB_HOST}:{self.DB_PORT}"
        #     f"/{self.DB_DATABASE}"
        # )


class RedisConfig(_BasicConfig):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USERNAME: str
    REDIS_PASSWORD: str
    REDIS_DB: int


class VectorDBConfig(_BasicConfig):
    VDB_BASE_URL: str = "https://paas-api.helixlife.dev/vector/v1"
    VDB_TIMEOUT_SECONDS: int
    VDB_REQUEST_INTERVAL: float = 0.05


class Config(
    DatabaseConfig,
    RedisConfig,
    ProjectConfig,
    VectorDBConfig,
): ...


config = Config()  # type: ignore
