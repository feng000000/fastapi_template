from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import ConfigDict, field_validator, model_validator
from sqlmodel import JSON, Column, Field, Index, SQLModel


# TODO: define Enum
class EnumField(str, Enum):
    field_1 = "field_1"
    field_2 = "field_2"


# TODO: define Table
class ExampleTable(SQLModel, table=True):
    model_config = ConfigDict(  # type: ignore
        arbitrary_types_allowed=True,  # allow to define `dict` field
        validate_assignment=True,  # validate field when create instance
    )
    __tablename__ = "example_tables"  # type: ignore[assignment]
    __table_args__ = (Index("user_email_idx", "email"),)

    id: UUID | None = Field(primary_key=True, default_factory=uuid4)

    email: str = Field(max_length=255, unique=True, nullable=False)

    table_info: dict = Field(sa_column=Column(JSON))

    enum_field: str = Field()

    created_at: datetime | None = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def set_update(self):
        self.model_config["validate_assignment"] = False  # type: ignore
        self.updated_at = datetime.now()
        self.model_config["validate_assignment"] = True  # type: ignore
        return self

    @field_validator("enum_field")
    @classmethod
    def validate_enum_field(cls, value) -> str:
        return EnumField(value).value
