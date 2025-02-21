import atexit
import fcntl
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class ProcessLock:
    def __init__(self, file_name: str = ".app.lock") -> None:
        file_lock = open(file_name, "wb")
        try:
            fcntl.flock(file_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock = True

            def unlock():
                fcntl.flock(file_lock, fcntl.LOCK_UN)
                file_lock.close()

            atexit.register(unlock)

        except Exception:
            self.lock = False

    def execute(
        self,
        func: Callable[..., T],
        *args,
        **kw,
    ) -> T:
        if self.lock:
            return func(*args, **kw)
        else:
            raise Exception(
                f"Process did not get the lock, so can not execute {func.__name__}"
            )
