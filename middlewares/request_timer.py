import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTimerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        _start = time.monotonic()

        response = await call_next(request)

        logger.info(f"request cost: {time.monotonic() - _start:.6f}s")

        return response
