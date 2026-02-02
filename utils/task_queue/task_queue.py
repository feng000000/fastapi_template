from __future__ import annotations

import asyncio
import inspect
import logging
import time
from asyncio import PriorityQueue
from collections.abc import Callable, Coroutine
from enum import IntEnum
from math import floor
from typing import Any

logger = logging.getLogger("AsyncTaskQueue")


class Task[**P, R]:
    """任务执行单元"""

    def __init__(
        self,
        callback: Callable[[R | Exception], None] | None,
        task: Callable[P, R] | Callable[P, Coroutine[Any, Any, R]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.future: asyncio.Future[R] = asyncio.Future()

        self._task_instance: asyncio.Task[R] | None = None

    async def exec(self) -> R | None:
        self._executed = True
        try:
            coro: Coroutine[Any, Any, R] = (  # type: ignore
                self.task(*self.args, **self.kwargs)
                if inspect.iscoroutinefunction(self.task)
                else asyncio.to_thread(self.task, *self.args, **self.kwargs)
            )
            self._task_instance = asyncio.create_task(coro)

            res = await self._task_instance
            self.future.set_result(res)
            return res
        except Exception as e:
            if self.callback:
                self.callback(e)
            self.future.set_exception(e)

    def cancel(self) -> None:
        if self._task_instance:
            self._task_instance.cancel()
            logger.debug(f"{self} canceled")


class RunnerStatus(IntEnum):
    """
    状态机:
    idle -> ready -> running -> idle
    """

    idle = 0
    running = 1
    ready = 2


class _Runner[**P, R]:
    def __init__(self):
        self.task: Task | None = None
        self.status: RunnerStatus = RunnerStatus.idle

    def register(self, task: Task):
        """将 _Task 注册到 Runner;

        如果 runner.status 不为 RunnerStatus.idle 会抛出 RuntimeError

        """
        if self.status != RunnerStatus.idle:
            raise RuntimeError(
                "can not register task to runner: runner is running"
            )
        self.task = task
        self.status = RunnerStatus.ready

    async def exec(self) -> None:
        if self.task is None:
            raise ValueError("Runner do not have a task")
        if self.status != RunnerStatus.ready:
            raise RuntimeError("Runner is not ready")

        self.status = RunnerStatus.running
        await self.task.exec()
        self.status = RunnerStatus.idle

    def __lt__(self, other: _Runner):
        """排序时 保证 空闲 runner 在前"""
        return self.status.value < other.status.value


class _RunnerPool:
    def __init__(self, max_qps: int | None, concurrence: int | None) -> None:
        """
        max_qps (int | None): 最大 QPS (包含 running 状态的任务)
        concurrence (int | None): 最大同时运行的任务

        """
        self.max_qps = max_qps
        self._qps_lock = asyncio.Lock()
        self._token = self.max_qps if self.max_qps else 0
        self._last_gen = time.monotonic()

        self.concurrence = concurrence

        self.pool: PriorityQueue[_Runner] = PriorityQueue()

        self._running_tasks: list[asyncio.Task] = []

    async def _get_qps_token(self) -> bool:
        """尝试获取 令牌 (qps 限制)"""
        if self.max_qps is None:
            return True

        got_token_flag = False

        await self._qps_lock.acquire()

        if self._token > 0:
            # logger.debug(f"token count: {self._token}")
            self._token -= 1
            got_token_flag = True

        _current = time.monotonic()
        _last_gen = self._last_gen
        # 计算这段时间内生成的令牌
        _gen_token = min(
            self.max_qps, floor(self.max_qps * (_current - _last_gen))
        )
        if _gen_token > 0:
            self._token += _gen_token - 1
            self._last_gen = _current
            got_token_flag = True

        self._qps_lock.release()

        # logger.debug(f"from last to current: {_current - _last_gen}")
        # logger.debug(f"gen_token: {_gen_token}")
        return got_token_flag

    async def execute(self) -> bool:
        """执行 runner, 执行数量受 qps, concurrence, 可执行的数量限制

        当没有可执行任务时返回 False
        """
        # logger.debug(f"\n>>>>>>>> pool info: {self}")
        if self.pool.empty():
            return False

        used_runners: list[_Runner] = []

        # 标志位
        have_more_task = False

        # 遍历顺序根据 RunnerStatus 从小到大
        while not self.pool.empty():
            runner = await self.pool.get()
            used_runners.append(runner)

            if runner.status == RunnerStatus.idle:
                continue

            if not await self._get_run_token(len(self._running_tasks)):
                # 此时可能是没有令牌, 视为 have_more_task
                have_more_task = True
                break

            if runner.status == RunnerStatus.running:
                have_more_task = True
            elif runner.status == RunnerStatus.ready:
                # 执行就绪状态的runner
                task = asyncio.create_task(runner.exec())
                task.add_done_callback(self._running_tasks.remove)
                self._running_tasks.append(task)
                have_more_task = True
                await asyncio.sleep(0)

        for runner in used_runners:
            await self.pool.put(runner)

        # if have_more_task:
        #     logger.debug(f"execute task number: {len(self._running_tasks)}")
        #     logger.debug(f"pool info: {self}")
        #     logger.debug(f"return have more task: {have_more_task}\n<<<<<<<<\n")

        return have_more_task

    async def _get_run_token(self, current_cnt: int) -> bool:
        """能否运行更多runner"""
        if self.concurrence and current_cnt >= self.concurrence:
            return False

        return await self._get_qps_token()

    async def push_task(self, task: Task) -> None:
        """添加任务进池子, 优先复用现有的空闲 Runner"""
        if self.pool.empty():
            logger.debug("push_task: empty pool, new runner")
            runner = _Runner()
        elif (
            top_runner := await self.pool.get()
        ) and top_runner.status != RunnerStatus.idle:
            await self.pool.put(top_runner)
            runner = _Runner()
            logger.debug("push_task: not idle runner, new runner")
        else:
            logger.debug("push_task: idle runner, new runner")
            runner = top_runner

        logger.debug(f"push task: {task}")
        runner.register(task)
        await self.pool.put(runner)

    def kill(self) -> None:
        """中止所有任务"""
        for item in self._running_tasks:
            item.cancel()

    def __repr__(self) -> str:
        """DEBUG 使用, 打印POOL 当前状态"""
        all_runners: list[_Runner] = []
        try:
            while True:
                all_runners.append(self.pool.get_nowait())
        except Exception:
            pass
        total = len(all_runners)
        idle = 0
        ready = 0
        running = 0
        for runner in all_runners:
            if runner.status == RunnerStatus.idle:
                idle += 1
            elif runner.status == RunnerStatus.ready:
                ready += 1
            elif runner.status == RunnerStatus.running:
                running += 1
            self.pool.put_nowait(runner)

        return (
            f"<RunnerPool 0x{hex(id(self))}\n"
            f"total number: {total}\n"
            f"idle number: {idle}\n"
            f"ready number: {ready}\n"
            f"running number: {running}"
            ">"
        )


class AsyncTaskQueue:
    def __init__(
        self,
        interval_s: float,
        concurrence: int | None = None,
        max_qps: int | None = None,
    ) -> None:
        """
        异步任务队列, 支持同步任务和异步任务

        Args:
            interval_s (float): 调度间隔时间, 单位 秒
            concurrence (int | None, optional):
                最大同时运行任务数, None 表示不限制. Defaults to None.
            max_qps (int | None, optional):
                最大 QPS, 包含正在运行任务的数量, None 表示不限制. Defaults to None.

        """
        self.running = False
        self._interval_s = interval_s
        self._schedule_instance: asyncio.Task | None = None
        self._wait_until_finish = False

        # 任务调度核心
        self.runner_pool = _RunnerPool(max_qps=max_qps, concurrence=concurrence)

    async def add_task[**P, R](
        self,
        callback: Callable[[R | Exception], None] | None,
        task: Callable[P, R] | Callable[P, Coroutine[Any, Any, R]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Task[P, R]:
        """
        添加任务进队列

        Returns:
            asyncio.Future: 可等待对象, 用于获取任务结果

        """
        new_task = Task(
            callback,
            task,
            *args,
            **kwargs,
        )
        await self.runner_pool.push_task(new_task)

        return new_task

    def down(self) -> None:
        """下次调度时停止"""
        self.running = False

    def kill(self) -> None:
        """强行停止, 正在执行的任务抛出 asyncio.CancelledError()"""
        self.runner_pool.kill()
        self.running = False

    async def schedule(self) -> None:
        """开始调度任务队列"""
        self.running = True
        self._schedule_instance = asyncio.create_task(self._schedule())

    async def wait_until_finish(self):
        self._wait_until_finish = True
        if self._schedule_instance:
            await self._schedule_instance

    async def _schedule(self) -> None:
        _debug = time.monotonic()
        while self.running:
            _c = time.monotonic()
            # logger.debug(f"scheduler cost: {_c - _debug:.3f}")
            _debug = _c

            have_more_task = await self.runner_pool.execute()
            logger.debug(f"schedule, have_more_task: {have_more_task}")

            # _wait_until_finish 时且已经没有任务执行了, 直接结束
            if self._wait_until_finish and not have_more_task:
                break
            await asyncio.sleep(self._interval_s)
