from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    field_validator,
    model_serializer,
    model_validator,
)


class CollectionField(BaseModel):
    data_type: Literal["text", "keyword", "int", "bool"]
    name: str


class Collection(BaseModel):
    collection_name: str
    extra_fields: list[CollectionField]

    @model_serializer
    def serializer(self):
        return {
            "collection_name": self.collection_name,
            "extra_field_schemas": self.extra_fields,
        }


class VectorDBStatusCode(int, Enum):
    """向量数据库响应json中code"""

    success = 2000
    internal_error = 3140
    data_error = 3160
    data_duplication = 3161


class RecordPropertyABC(ABC):
    def __init__(self, doc_id: str, text: str):
        self.doc_id = doc_id
        self.text = text

    @abstractmethod
    def properties(self) -> dict:
        return {
            "doc_id": self.doc_id,  # 数据主键
            "text": self.text,  # 文档的文本
        }


class Filter(BaseModel):
    field_name: str
    value: list[str] | str
    operator: Literal["equal", "contains_any"] = "equal"

    @field_validator("value")
    @classmethod
    def value_validator(cls, v: Any):
        if isinstance(v, list):
            assert len(v) < 100, f"`doc_id` filters must <= 100 ({v})"
        return v


class _RetrievalConfig(BaseModel):
    limit: int = 10
    offset: float | None = None
    alpha: float | None = None
    distance: float | None = None
    search_method: Literal[
        "semantic_search",
        "full_text_search",
        "hybrid_search",
    ] = "semantic_search"

    @field_validator("limit")
    @classmethod
    def limit_validator(cls, v: Any):
        v = int(v)
        assert (
            v >= 1 and v < 100
        ), f"retrieval_config.limit must belongs [1, 100] ({v})"
        return v

    @field_validator("alpha")
    @classmethod
    def alpha_validator(cls, v: Any):
        v = float(v)
        assert (
            v > 0 and v <= 1
        ), f"retrieval_config.alpha must belongs (0, 1] ({v})"
        return v


class QueryParam(BaseModel):
    query: str
    filters: list[Filter] = []
    retrieval_config: _RetrievalConfig = _RetrievalConfig()

    @model_validator(mode="after")
    def value_validator(self):
        doc_id_filter_num = 0
        for item in self.filters:
            if item.field_name != "doc_id":
                continue

            if item.operator == "equal":
                doc_id_filter_num += 1
            elif item.operator == "contains_any":
                doc_id_filter_num += len(item.value)

        assert (
            doc_id_filter_num <= 100
        ), f"`doc_id` filters must <= 100 ({doc_id_filter_num})"
        return self
