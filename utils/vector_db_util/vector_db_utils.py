import asyncio
import json
import logging
import time
from collections.abc import Coroutine
from typing import Any, Literal, TypeVar

import httpx

from config import config
from utils.task_queue import TaskQueue

from .exceptions import VectorDBError
from .schemas import (
    Collection,
    Filter,
    QueryParam,
    RecordPropertyABC,
    VectorDBStatusCode,
)

logger = logging.getLogger(__name__)


VECTOR_DB_ASYNC_CLIENT = httpx.AsyncClient(timeout=config.VDB_TIMEOUT_SECONDS)

RecordProperty = TypeVar("RecordProperty", bound=RecordPropertyABC)

_RECORD_LIMIT = 100


def short_msg(data: Any, length: int = 256) -> str:
    s = json.dumps(data, ensure_ascii=False)
    if len(s) > length:
        s = s[:length] + "..."
    return s


def _error_log(res: dict) -> str | None:
    """根据向量数据库响应, 记录错误日志"""
    error_msg = res.get("msg")
    if res.get("code") == VectorDBStatusCode.success:
        return None
    logger.warning(
        f"request failed, code: {res.get('code', None)}\n"
        f"msg: {res.get('msg')}\n"
        f"raw_response: {res}\n"
    )
    return error_msg


class _RequestLimiter:
    _task_queue = TaskQueue(interval=config.VDB_REQUEST_INTERVAL)

    @classmethod
    def _schedule_task(cls, coro: Coroutine):
        if not cls._task_queue.running:
            cls._task_queue.schedule()

        return cls._task_queue.add_task(coro)

    @classmethod
    async def request_vector_db(
        cls,
        method: Literal["post", "get", "delete", "put"],
        endpoint: str,
        headers: dict,
        json_body: Any,
    ) -> dict:
        """
        请求向量数据库

        Args:
            endpoint (str): endpoint must start with "/"
            json (Any):
            collection_name (str):
            method (Literal["post", "get", "delete", "put"]):

        Returns:
            dict: 响应体json

        """

        async def operation():
            """发送请求"""
            url = f"{config.VDB_BASE_URL.strip('/')}{endpoint}"

            logger.info(f"request vector db, url: {url}")

            req_start_time = time.time()
            try:
                res = await VECTOR_DB_ASYNC_CLIENT.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_body,
                    timeout=300,
                )
            except httpx.TimeoutException as e:
                req_timeout_time = time.time()
                logger.warning(
                    f"error: {type(e), e}, "
                    f"cost: {req_timeout_time - req_start_time} seconds"
                )
                raise e

            if res.status_code != 200:
                logger.error(
                    f"request vector db failed\n"
                    f"url: {url}\n"
                    f"headers: {headers}\n"
                    f"json: {short_msg(json_body)}\n"
                    f"status_code: [{res.status_code}], {res.content}\n"
                )

                raise Exception("request vector db failed")
            json_data = res.json()

            logger.info(
                f"url: {url}\n"
                f"headers: {headers}\n"
                f"json: {short_msg(json_body)}\n"
                f"response json res: {short_msg(json_data)}\n"
            )
            return json_data

        res: dict = await cls._schedule_task(operation())
        return res


class VectorDBOperator:
    @staticmethod
    async def create_collection(collection: Collection) -> None:
        json_res = await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/collection/create",
            headers={},
            json_body=collection.model_dump(),
        )
        if json_res["code"] != VectorDBStatusCode.success:
            raise Exception(json_res)

    @staticmethod
    async def delete_collection(collection_name: str) -> None:
        json_res = await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/collection/delete",
            headers={},
            json_body={"collection_name": collection_name},
        )
        if json_res["code"] != VectorDBStatusCode.success:
            raise Exception(json_res)

    @staticmethod
    async def add_records(
        type_: Literal["text", "text_json", "text_html"],
        records: list[RecordProperty],
        collection_name: str,
        retry_times: int = 2,
    ) -> list[bool]:
        """
        添加记录到向量数据库

        Args:
            type_ (Literal["text", "text_json", "text_html"]):
                请求的 body 中的 `type` 字段
            records (list[RecordProperty]): 要添加的向量数据库的记录
            collection_name (CollectionName):
            retry_times (int, optional): 失败重试次数, 会去掉对应的失败id后再重试.
                Defaults to 2.

        Returns:
            list[bool]: 返回添加状态, 是否成功

        """
        global _RECORD_LIMIT

        if len(records) > _RECORD_LIMIT:
            idx = 0
            task_list: list[asyncio.Task[list[bool]]] = []
            while idx < len(records):
                task_list.append(
                    asyncio.create_task(
                        VectorDBOperator.add_records(
                            type_=type_,
                            records=records[idx : idx + _RECORD_LIMIT],
                            collection_name=collection_name,
                        )
                    )
                )
                idx += _RECORD_LIMIT
            results: list[bool] = []
            for task in task_list:
                results.extend(await task)

            return results

        if not records:
            return []

        failed_ids = []
        req_records = records.copy()
        for i in range(retry_times + 1):
            logger.debug(f"add doc to {collection_name}, times index: {i}")

            _failed_ids = await VectorDBOperator._try_add_records(
                collection_name=collection_name,
                type_=type_,
                records=req_records,
            )
            if _failed_ids == []:
                break

            failed_ids.extend(_failed_ids)

            # 更新records, 去掉失败id, 在下一次循环重试
            req_records = [
                item for item in req_records if item.doc_id not in _failed_ids
            ]

        return [item.doc_id not in failed_ids for item in records]

    @staticmethod
    async def _try_add_records(
        collection_name: str,
        type_: Literal["text", "text_json", "text_html"],
        records: list[RecordProperty],
    ) -> list[str]:
        """
        尝试添加记录, 已存在记录会尝试调用更新接口

        Args:
            collection_name (str): 数据库名
            type_ (Literal["text", "text_json", "text_html"]):
                请求的 body 中的 `type` 字段
            records (list[RecordProperty]): 请求的 body 中的 `data` 字段

        Returns:
            list[str]: 返回失败 id

        """
        if not records:
            return []

        _data = [{"properties": record.properties()} for record in records]
        json_res = await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/documents/create",
            headers={"collection-name": collection_name},
            json_body={
                "type": type_,
                "data": _data,
                "segmentation": {
                    "chunk_size": 0,
                    "chunk_overlap": 0,
                    "separators": ["(?!)"],
                },
            },
        )
        if json_res["code"] == VectorDBStatusCode.success:
            return []

        # 去除重复 id 然后重试, 重复的 id 去调更新接口
        if "duplicate_ids" in json_res.get("data", {}):
            msg = _error_log(json_res)

            failed_ids = await VectorDBOperator._try_update_record(
                type_=type_,
                collection_name=collection_name,
                records=[
                    item
                    for item in records
                    if item.doc_id not in json_res["data"]["duplicate_ids"]
                ],
            )

        # 去除失败 id 然后重试
        elif "failed_ids" in json_res.get("data", {}):
            msg = _error_log(json_res)
            failed_ids = json_res["data"]["failed_ids"]

        else:
            msg = _error_log(json_res)
            raise Exception(f"Vector Database error: {msg}")

        return failed_ids

    @staticmethod
    async def query_record(
        collection_name: str,
        query_param: QueryParam,
    ) -> list[dict]:
        """
        查询记录

        Args:
            doc_id (str): 要查询的记录 id
            collection_name (CollectionName):
                企微, CollectionName.wechatcom; 飞书, CollectionName.lark.

        Returns:
            list[dict]: 响应的 data 字段

        """
        json_data = await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/documents/search",
            headers={"collection-name": collection_name},
            json_body=query_param.model_dump(exclude_none=True),
        )

        if json_data.get("code") != VectorDBStatusCode.success:
            msg = _error_log(json_data)
            raise VectorDBError(
                f"query record failed\n"
                f"query_param: {query_param}, error msg: {msg}\n"
                f"json_data: {json_data}\n"
            )

        return json_data["data"]

    @staticmethod
    async def update_record(
        type_: Literal["text", "text_json", "text_html"],
        records: list[RecordProperty],
        collection_name: str,
        retry_times: int = 2,
    ) -> list[bool]:
        """
        编辑飞书同步记录

        Args:
            json (dict | None):
                如果传入 `json` 则忽略其他参数, 直接作为请求体请求
            record (RecordProperty | None): 要编辑的记录
            req_type (Literal["text", "text_json"]  | None):
                表示 `record.text` 是 `普通字符串` 还是 `json字符串`

        """
        global _RECORD_LIMIT

        if len(records) > _RECORD_LIMIT:
            idx = 0
            task_list: list[asyncio.Task[list[bool]]] = []
            while idx < len(records):
                task_list.append(
                    asyncio.create_task(
                        VectorDBOperator.update_record(
                            type_=type_,
                            records=records[idx : idx + _RECORD_LIMIT],
                            collection_name=collection_name,
                        )
                    )
                )
                idx += _RECORD_LIMIT
            result: list[bool] = []
            for task in task_list:
                result.extend(await task)
            return result

        failed_ids = []
        req_records = records.copy()
        for i in range(retry_times + 1):
            logger.debug(f"update to {collection_name}, times index {i}")

            _failed_ids = await VectorDBOperator._try_update_record(
                type_=type_,
                records=req_records,
                collection_name=collection_name,
            )
            if _failed_ids == []:
                break

            failed_ids.extend(_failed_ids)

            # 更新records, 去掉失败id, 在下一次循环重试
            req_records = [
                item for item in req_records if item.doc_id not in _failed_ids
            ]

        return [item.doc_id not in failed_ids for item in records]

    @staticmethod
    async def _try_update_record(
        type_: Literal["text", "text_json", "text_html"],
        collection_name: str,
        records: list[RecordProperty],
    ) -> list[str]:
        json_res = await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/documents/update",
            headers={"collection-name": collection_name},
            json_body={
                "type": type_,
                "data": [item.properties() for item in records],
            },
        )

        if json_res.get("code") == VectorDBStatusCode.success:
            return []

        if "duplicate_ids" in json_res.get("data", {}):
            """去除重复 id 然后重试, 重复的 id 去调更新接口"""
            _ = _error_log(json_res)
            failed_ids: list = json_res["data"]["duplicate_ids"]
        elif "failed_ids" in json_res.get("data", {}):
            """去除失败 id 然后重试"""
            _ = _error_log(json_res)
            failed_ids = json_res["data"]["failed_ids"]
        else:
            msg = _error_log(json_res)
            raise Exception(f"Vector Database error: {msg}")

        return failed_ids

    @staticmethod
    async def delete_record(
        collection_name: str,
        filters: list[Filter],
    ):
        """
        删除记录

        Args:
            collection_name (str):
            filters (list[Filter]): 筛选条件

        """
        await _RequestLimiter.request_vector_db(
            method="post",
            endpoint="/documents/delete",
            headers={"collection-name": collection_name},
            json_body={"filters": [item.model_dump() for item in filters]},
        )
