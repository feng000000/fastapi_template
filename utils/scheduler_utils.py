import logging
from collections.abc import Callable
from functools import wraps

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("SCHEDULER")

_SCHEDULER = AsyncIOScheduler()

_TASKS_SET = set()


def start_scheduler():
    global _SCHEDULER
    _SCHEDULER.start()


def add_schedule_task(
    task_name: str,
    task: Callable,
    trigger: CronTrigger | IntervalTrigger | DateTrigger,
):
    """
    添加定时任务

    Args:
        task_name (str): 任务名
        task (Callable): 任务函数 (支持同步函数和协程函数)
        trigger (CronTrigger | IntervalTrigger | DateTrigger): 触发器

    """
    global _TASKS_SET
    global _SCHEDULER

    if task_name in _TASKS_SET:
        logger.error(f"task {task_name} already registered")
    else:
        _TASKS_SET.add(task_name)
        _SCHEDULER.add_job(func=task, id=task_name, trigger=trigger)


def schedule_task(
    task_name: str,
    trigger: CronTrigger | IntervalTrigger | DateTrigger,
):
    """
    将一个函数注册为定时任务

    ### Usage:
    ```python
    from apscheduler.triggers.interval import IntervalTrigger

    @schedule("task_1", IntervalTrigger(seconds=2))
    def task1():
        ...

    @schedule("task_2", IntervalTrigger(seconds=2))
    async def task2():
        ...
    ```

    Args:
        task_name (str): 任务名
        trigger (CronTrigger | IntervalTrigger | DateTrigger): 触发器

    """

    def decorator(func: Callable):
        add_schedule_task(task=func, task_name=task_name, trigger=trigger)

        @wraps
        def wrapper(*arg, **kw):
            return func(*arg, **kw)

        return wrapper

    return decorator
