# tests/__init__.py
from __future__ import annotations

import asyncio
import traceback
from collections.abc import Callable
from typing import Any

CONFIG: dict[str, Any] = {}

_TestFunc = Callable[[], Any]

_ALL_TASK: dict[int, _TestTask] = {}


class _TestNode:
    def __init__(
        self,
        name: str,
        func: _TestFunc,
        sons: list[_TestNode],
        degree: int = 0,
    ) -> None:
        self.name = name
        self.func = func
        self.sons = sons
        self.degree = degree
        self.executed = False


class _TestTask:
    def __init__(
        self,
        tag: str,
        func: _TestFunc,
        dependencies: list[_TestFunc] | None,
    ) -> None:
        self.tag = tag
        self.func = func
        self.dependencies = dependencies if dependencies else []


# 装饰器, 用于添加测试函数
def test_task(
    tag: str,
    *,
    dependencies: list[_TestFunc] | None = None,
):
    global _ALL_TASK

    def wrapper(func: _TestFunc):
        _ALL_TASK[id(func)] = _TestTask(
            tag=tag,
            func=func,
            dependencies=dependencies,
        )
        # print(f"func: {func}, dependencies: {dependencies}")
        return func

    return wrapper


class TestTree:
    def __init__(
        self,
        nodes: dict[int, _TestNode],
        ancestors: list[int],
    ) -> None:
        self.nodes = nodes
        self.ancestors = ancestors

    async def execute(self):
        """execute all tasks"""

        def _print_msg(task: asyncio.Task):
            try:
                _ = task.result()
                print(
                    f"\033[34m[TEST CHAIN] {task.get_name()}\033[0m"
                    f"\033[32m PASSED \033[0m"
                )
            except Exception as e:
                print(
                    f"\033[34m[TEST CHAIN] {task.get_name()}\033[0m"
                    f"\033[31m FAILED\n"
                    f"error: {type(e)}, {e}\n"
                    f"traceback: {traceback.format_exc()}\033[0m"
                )

        tasks: list[asyncio.Task] = []
        for key in self.ancestors:
            task = asyncio.create_task(
                self._execute(self.nodes[key]),
                name=self.nodes[key].name,
            )
            task.add_done_callback(_print_msg)
            tasks.append(task)

        for task in tasks:
            await task

    async def _execute(self, node: _TestNode):
        tmp = node.func()
        if asyncio.iscoroutine(tmp):
            await asyncio.create_task(tmp)

        print(f"  [TEST] {node.name} success")

        node.executed = True

        for son in node.sons:
            await self._execute(son)

    # 构建测试任务树
    @staticmethod
    def build(
        all_test: dict[int, _TestTask] = _ALL_TASK,
    ) -> TestTree:
        nodes: dict[int, _TestNode] = {}

        ancestors = []

        def _dfs(task: _TestTask, son: _TestNode | None = None):
            key = id(task.func)
            if not nodes.get(key):
                nodes[key] = _TestNode(
                    name=f"{task.tag}: {task.func.__name__}",
                    func=task.func,
                    sons=[],
                )

            nodes[key].degree += 1
            if son and son not in nodes[key].sons:
                nodes[key].sons.append(son)
            if not task.dependencies and key not in ancestors:
                ancestors.append(key)
            for dep in task.dependencies:
                _dfs(all_test[id(dep)], son=nodes[key])

        [_dfs(test) for _, test in all_test.items()]

        return TestTree(nodes=nodes, ancestors=ancestors)
