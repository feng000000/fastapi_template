import logging

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CustomerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # TODO: operations before request

        response = await call_next(request)

        # TODO: operations after request

        return response
