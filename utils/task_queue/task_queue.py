import asyncio
import logging
from asyncio import Event, Future, Task
from asyncio.queues import Queue
from collections.abc import Awaitable

logger = logging.getLogger(__name__)


class _CustomTask:
    def __init__(self, coro: Awaitable, future: Future) -> None:
        self.coro = coro
        self.future = future


class TaskQueue:
    def __init__(self, interval: float, size: int = -1) -> None:
        self._task_queue = Queue(size)
        self._interval = interval
        self.running = False

        self._finish_task_event = Event()
        self._running_task_num = 0
        self._running_task = set()

    def add_task(self, coro: Awaitable) -> Future:
        future = Future()
        new_task = _CustomTask(
            coro=coro,
            future=future,
        )
        self._task_queue.put_nowait(new_task)

        return future

    def schedule(self) -> Task:
        self.running = True
        return asyncio.create_task(self._schedule())

    async def _schedule(self) -> None:
        while True:
            task: _CustomTask = await self._task_queue.get()

            self._running_task_num += 1
            asyncio_task = asyncio.create_task(self._execute_task(task))
            self._running_task.add(asyncio_task)
            asyncio_task.add_done_callback(self._running_task.discard)

            await asyncio.sleep(self._interval)

    async def _execute_task(self, task: _CustomTask):
        try:
            res = await task.coro
            task.future.set_result(res)
        except Exception as e:
            logger.error(
                f"got a error: {type(e)}, {e}\ntask: {task.coro.__qualname__}\n"
            )
            task.future.set_exception(e)

        self._running_task_num -= 1
        self._finish_task_event.set()

    async def wait_until_finish(self):
        while True:
            await self._finish_task_event.wait()
            if self._running_task_num == 0 and self._task_queue.qsize() == 0:
                logger.info("task queue finished")
                return
            self._finish_task_event.clear()


_global_task_queue = None


def get_global_task_queue(interval: int = 6) -> TaskQueue:
    global _global_task_queue

    if _global_task_queue is None:
        _global_task_queue = TaskQueue(interval=interval)

    return _global_task_queue
