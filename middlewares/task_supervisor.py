import asyncio
import logging
from asyncio import Queue
from collections.abc import Iterable
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message, Receive, Scope, Send

_REQUEST_TASK: dict[str, list[asyncio.Task]] = {}

_REQUEST_ID: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

logger = logging.getLogger(__name__)


def supervise_tasks(tasks: Iterable[asyncio.Task]):
    """
    监管任务, 请求被中断时取消任务

    Args:
        tasks (list[asyncio.Task]): 要监管的任务列表

    """
    global _REQUEST_ID
    global _REQUEST_TASK

    request_id = _REQUEST_ID.get()
    logger.debug(f"supervise task on {request_id}")
    if request_id in _REQUEST_TASK:
        _REQUEST_TASK[request_id].extend(tasks)


def cancel_tasks() -> bool:
    """
    清除当前请求下已监管的任务 ( `supervise_task()` )

    Returns:
        bool: 如果request_id 为 None, 返回 False, 否则 返回 True

    """
    global _REQUEST_ID
    global _REQUEST_TASK

    request_id = _REQUEST_ID.get()
    if request_id is None:
        return False

    target_tasks = _REQUEST_TASK[request_id]
    logger.debug(f"cancel tasks on {request_id}: {len(target_tasks)}")
    for task in target_tasks:
        cancel_res = task.cancel()
        logger.debug(f"cancel result: {cancel_res} ({task})")
    _REQUEST_TASK.pop(request_id)

    return True


class _ReceiveWrapper:
    def __init__(self, receive: Receive) -> None:
        self.rcv = receive
        self.origin_list: Queue[Message] = Queue()
        self.wrapper_list: Queue[Message] = Queue()

    async def _receive(self):
        msg = await self.rcv()
        await self.origin_list.put(msg)
        await self.wrapper_list.put(msg)

    async def _get_from_origin(self):
        if self.origin_list.empty():
            await self._receive()

        msg = await self.origin_list.get()
        return msg

    async def _get_from_wrapper(self):
        if self.wrapper_list.empty():
            await self._receive()

        msg = await self.wrapper_list.get()
        return msg

    async def rcv_origin(self):
        return await self._get_from_origin()

    async def rcv_wrapper(self):
        return await self._get_from_wrapper()


class SuperviseTaskMiddleware(BaseHTTPMiddleware):
    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        global _REQUEST_TASK
        global _REQUEST_ID

        logger.debug(f"SupervisorTaskMiddleware scope: {scope}")
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return None

        request_id = f"req_id_{str(uuid4())}"
        token = _REQUEST_ID.set(request_id)
        _REQUEST_TASK[request_id] = []

        rcv_wrapper = _ReceiveWrapper(receive=receive)

        async def handle_disconnect(_receive: Receive):
            while True:
                res = await _receive()
                logger.debug(f"SupervisorTask receive type: {res['type']}")
                if res["type"] == "http.disconnect":
                    return True

        async def handle_app(_receive: Receive):
            try:
                await self.app(scope, _receive, send)
            except asyncio.CancelledError:
                logger.info(f"request {request_id} cancelled")
                pass

        # async run `handle disconnect message` and `main logic`
        handle_disconnect_task = asyncio.create_task(
            handle_disconnect(rcv_wrapper.rcv_origin)
        )
        app_task = asyncio.create_task(handle_app(rcv_wrapper.rcv_wrapper))

        # stop when first completed
        done, pending = await asyncio.wait(
            [handle_disconnect_task, app_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        cancel_flag = None
        for task in done:
            logger.debug(f"done task: {task}")
            if task == app_task:
                cancel_flag = False
            if task == handle_disconnect_task and cancel_flag != False:
                cancel_flag = True

            # retrieve exception
            await task

        # if app_task not done and handle_disconnect_task done:
        if cancel_flag:
            cancel_tasks()

        [task.cancel() for task in pending]

        _REQUEST_ID.reset(token)
