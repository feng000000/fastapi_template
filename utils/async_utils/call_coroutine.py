import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from threading import current_thread, main_thread
from typing import Any, TypeVar

T = TypeVar("T")


def call_coroutine(coro: Coroutine[Any, Any, T], timeout: float = 30) -> T:
    """
    用于在同步函数中调用异步函数

    Args:
        coro (Coroutine): 要运行的 Coroutine

    """

    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if current_thread() is main_thread():
        if not loop.is_running():
            return loop.run_until_complete(coro)
        else:
            with ThreadPoolExecutor() as pool:
                future = pool.submit(run_in_new_loop)
                return future.result(timeout=timeout)
    else:
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
