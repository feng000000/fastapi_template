import logging

from filelock import FileLock

from config import config
from db.models import PartitionTableExample
from utils.scheduler_util import (
    IntervalTrigger,
    add_schedule_task,
    start_scheduler,
)


_FILELOCK = FileLock(".apscheduler.lock", timeout=0.05)

logger = logging.getLogger(__name__)


def init_schedule_task():
    try:
        global _FILELOCK
        _FILELOCK.acquire()
    except Exception:
        logger.debug("cannot get the apscheduler.lock")
        return

    async def _update_partition_table():
        await PartitionTableExample.update_partition_table()
        # await OtherTable.update_partition_table()

    add_schedule_task(
        "create_partition_table",
        _update_partition_table,
        trigger=IntervalTrigger(days=1),
    )

    start_scheduler()
