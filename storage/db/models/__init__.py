from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Index, SQLModel  # noqa F401

from utils.sqlmodel_patch import AUTO_UPDATE, ProxySQLModel


# TODO: define Enum
class EnumField(str, Enum):
    field_1 = "field_1"
    field_2 = "field_2"


# TODO: define Table
class ExampleTable(ProxySQLModel, table=True):
    __tablename__ = "example_tables"  # type: ignore[assignment]
    __table_args__ = (Index("user_email_idx", "email"),)

    id: UUID | None = Field(primary_key=True, default_factory=uuid4)

    email: str = Field(max_length=255, unique=True, nullable=False)

    # dict/list data
    # table_info: dict

    enum_field: EnumField

    __auto_timestamps__ = True
    # or
    update_at: AUTO_UPDATE
