import os
from functools import cached_property
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _BasicSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="./docker/.env")


class ProjectSettings(_BasicSettings):
    # TODO: update ProjectSettings
    LOG_FILE_PATH: str = Field()
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field()

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


class DatabaseSettings(_BasicSettings):
    DB_HOST: str = Field()
    DB_PORT: str = Field()
    DB_USRENAME: str = Field()
    DB_PASSWORD: str = Field()
    DB_DATABASE: str = Field()

    @cached_property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return (
            "postgresql://"
            f"{self.DB_USRENAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}"
            f"/{self.DB_DATABASE}"
        )


class RedisSettings(_BasicSettings):
    REDIS_HOST: str = Field()
    REDIS_PORT: int = Field()
    REDIS_PASSWORD: str = Field()
    REDIS_DB: int = Field()

    @cached_property
    def REDIS_URL(self) -> str:  # noqa: N802
        return (
            "redis://"
            f":{self.REDIS_PASSWORD}"
            f"@{self.REDIS_HOST}:{self.REDIS_PORT}"
            f"/{self.REDIS_DB}"
        )


class Settings(
    DatabaseSettings,
    RedisSettings,
    ProjectSettings,
): ...


settings = Settings()  # type: ignore
