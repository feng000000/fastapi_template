from datetime import datetime
from enum import Enum
from typing import Annotated, TypeAlias
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlmodel import JSON, Column, Field, Index, SQLModel

AUTO_UPDATE: TypeAlias = Annotated[
    datetime | None,
    Field(
        default_factory=datetime.now,
        nullable=False,
        sa_column_kwargs={
            "onupdate": datetime.now,
        },
    ),
]


# TODO: define Enum
class EnumField(str, Enum):
    field_1 = "field_1"
    field_2 = "field_2"


# TODO: define Table
class ExampleTable(SQLModel, table=True):
    model_config = ConfigDict(  # type: ignore
        # # 允许定义 `dict` 字段
        arbitrary_types_allowed=True,
        # 在创建实例时进行验证
        validate_assignment=True,
    )

    __tablename__ = "example_tables"  # type: ignore[assignment]
    __table_args__ = (Index("user_email_idx", "email"),)

    id: UUID | None = Field(primary_key=True, default_factory=uuid4)

    email: str = Field(max_length=255, unique=True, nullable=False)

    # dict/list data
    table_info: dict = Field(sa_column=Column(JSON))

    enum_field: EnumField

    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: AUTO_UPDATE
