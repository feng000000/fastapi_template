import asyncio
from asyncio import Task
from collections.abc import Coroutine
from typing import Any


class TaskGroup:
    def __init__(
        self, coros: list[Coroutine] | None = None, batch_size: int = -1
    ) -> None:
        """
        TaskGroup 用于并行执行任务, 使用 `get()` 或 `get_noexcept()` 获取执行结果

        Usage
        ```python
            task_group = TaskGroup(coros = [
                async_func1("xxx")
                async_func2("xxx")
            ])
            task_group.append(async_func2("xxx"))
            res: list = await task_group.get()
        ```

        Args:
            coros (list[Awaitable], optional): 任务列表. Defaults to [].
            batch_size: 并行执行的最大任务数, 如果 `len(coros) > batch_size` 会分批次执行.
                `-1` 代表不限制

        """
        self._batch_size = batch_size
        self._coro_group: list[Coroutine] = []
        if coros is not None:
            for coro in coros:
                self._coro_group.append(coro)

    def append(self, coro: Coroutine) -> None:
        """
        向Group中添加一个异步任务

        Args:
            func (Awaitable):

        """
        self._coro_group.append(coro)

    async def _create_tasks(self, coros: list[Coroutine]) -> list[Task]:
        """
        通过 asyncio.create_task 创建 Task

        """
        tasks: list[Task] = []
        for coro in coros:
            task = asyncio.create_task(coro)
            tasks.append(task)
        return tasks

    async def _schedule_tasks(self, tasks: list[Task]) -> list:
        """
        异步执行 tasks

        """
        res_list = []
        for task in tasks:
            res_list.append(await task)
        return res_list

    async def _schedule_tasks_noexcept(self, tasks: list[Task]) -> list:
        """
        异常安全地异步执行 tasks, 如果发生异常返回值则为对应的 Exception

        """
        res_list = []
        for task in tasks:
            try:
                res_list.append(await task)
            except Exception as e:
                res_list.append(e)
                # res_list.append((e, traceback.format_exc()))
        return res_list

    def execute(self) -> None:
        """
        执行 TaskGroup中的任务, 不关心返回结果, 仍然会抛出异常

        """
        asyncio.create_task(self.get())

    async def get(self) -> list[Any]:
        """
        异步执行任务, 任务全部完成时, 返回结果列表.
        任务发生异常时直接抛出

        Returns:
            list[Any]: 函数执行的结果集

        """
        res_list = []

        if self._batch_size == -1:
            tasks = await self._create_tasks(self._coro_group)
            return await self._schedule_tasks(tasks)

        current_num = 0
        while current_num < len(self._coro_group):
            start = current_num
            end = current_num + self._batch_size

            tasks = await self._create_tasks(self._coro_group[start:end])
            res = await self._schedule_tasks(tasks)
            res_list.extend(res)

            current_num = end

        return res_list

    async def get_noexcept(self) -> list[Any]:
        """
        异步执行任务, 任务全部完成时, 返回结果列表.
        该函数不会抛出异常,
        任务发生异常时, 返回列表中对应任务的值为抛出的异常

        Returns:
            list[Any]: 函数执行的结果集

        """
        res_list = []

        if self._batch_size == -1:
            tasks = await self._create_tasks(self._coro_group)
            return await self._schedule_tasks_noexcept(tasks)

        current_num = 0
        while current_num < len(self._coro_group):
            start = current_num
            end = current_num + self._batch_size

            tasks = await self._create_tasks(self._coro_group[start:end])
            res = await self._schedule_tasks_noexcept(tasks)
            res_list.extend(res)

            current_num = end

        return res_list
