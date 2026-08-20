from datetime import datetime, UTC
from enum import StrEnum
from uuid import UUID, uuid4

from logging import getLogger

from dateutil.relativedelta import relativedelta

from pydantic import ConfigDict
from sqlmodel import DateTime
from sqlmodel import JSON, Column, Field, Index, SQLModel
from sqlalchemy.dialects.postgresql import JSONB


from .. import db

logger = getLogger(__name__)


# AUTO_UPDATE = Field(
#     default_factory=datetime.now,
#     nullable=False,
#     sa_column_kwargs={
#         "onupdate": datetime.now,
#     },
# )

def AutoUpdateField():
    return Field(
        default_factory=lambda:datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda:datetime.now(UTC),
            onupdate=lambda:datetime.now(UTC),
        ),
    )

# TODO: define Enum
class EnumField(StrEnum):
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
    table_info_jsonb: dict = Field(sa_column=Column(JSONB, default={}))

    # 1. 新建表时指定 Enum 列, 迁移脚本直接使用
    #   sa.Column('xxx', sa.Enum('enum1', 'enum2', name='enum_name')
    #   即可
    # 2. 如果是修改现有列为 Enum 列, 需要手动创建 Enum
    #   enum_name = sa.Enum('xxx', 'enum1', 'enum2', name='enum_name')
    #   enum_name.create(op.get_bind())
    # -1. downgrade() 中需要删除 创建的 Enum
    #   sa.Enum(name='enum_name').drop(op.get_bind())
    enum_field: EnumField

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = AutoUpdateField()


class PartitionTableExample(SQLModel, table=True):

    model_config = ConfigDict(  # type: ignore
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    __tablename__ = "moderation_records"  # type: ignore

    __table_args__ = ({"postgresql_partition_by": "RANGE (created_at)"},)

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    @classmethod
    async def update_partition_table(cls):
        """创建 当前月 和 下月 的分区表"""
        table_name = str(cls.__tablename__)

        async def create_date_partition_table(date_: datetime):
            date_ = date_.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            next_month = date_ + relativedelta(months=1)
            partition_name = f"{table_name}_{date_.year:4}_{date_.month:02}"
            start = date_.strftime("%Y-%m-%d %H:%M:%S%z")
            end = next_month.strftime("%Y-%m-%d %H:%M:%S%z")

            await db.create_partition_table_on_postgres(
                table_name=table_name,
                partition_name=partition_name,
                start=start,
                end=end,
            )

        try:
            current = datetime.now(UTC)
            await create_date_partition_table(current)

            next_month = current + relativedelta(months=1)
            await create_date_partition_table(next_month)
        except Exception as e:
            logger.error(f"failed create partitions: {type(e), e}")
