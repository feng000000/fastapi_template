from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import ConfigDict, model_serializer, model_validator
from pydantic.dataclasses import dataclass
from sqlmodel import JSON, Column, Field, SQLModel
from sqlmodel.main import SQLModelMetaclass

AUTO_UPDATE = Annotated[
    datetime | None,
    Field(
        default_factory=datetime.now,
        nullable=False,
        sa_column_kwargs={
            "onupdate": datetime.now,
        },
    ),
]


@dataclass
class ProxyEnum(Enum):
    @model_serializer
    def serialize(self):
        return self.value


class ProxySQLModelMetaclass(SQLModelMetaclass):
    def __new__(cls, name, bases, dct, **kwargs):
        for k, v in dct["__annotations__"].items():
            if isinstance(v, list) or isinstance(v, dict):
                dct[k] = Field(sa_column=Column(JSON))

        if dct.get("__auto_timestamps__", False):
            dct["created_at"] = Field(
                default_factory=datetime.now, nullable=False
            )
            dct["updated_at"] = Field(
                default_factory=datetime.now, nullable=False
            )
            dct["__annotations__"]["created_at"] = datetime
            dct["__annotations__"]["updated_at"] = datetime

            @model_validator(mode="after")
            def set_updated_at(self):
                self.model_config["validate_assignment"] = False
                self.updated_at = datetime.now()
                self.model_config["validate_assignment"] = True
                return self

            dct["set_updated_at"] = set_updated_at

        return super().__new__(cls, name, bases, dct, **kwargs)


class ProxySQLModel(SQLModel, metaclass=ProxySQLModelMetaclass):
    model_config = ConfigDict(  # type: ignore
        # # 允许定义 `dict` 字段
        arbitrary_types_allowed=True,
        # 在创建实例时进行验证
        validate_assignment=True,
    )

    # 是否自动添加 `create_at` 和 `update_at` 属性
    __auto_timestamps__: bool = False
