import logging
import time
import uuid

from starlette.types import Message, Receive, Scope, Send

logger = logging.getLogger("REQUEST_TIMER")


# starlette.BaseHTTPMiddleware 写法
# from starlette.middleware.base import BaseHTTPMiddleware
# class RequestTimerMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         _start = time.monotonic()

#         response = await call_next(request)

#         logger.info(f"request cost: {time.monotonic() - _start:.6f}s")

#         return response


# ASGI 中间件写法
class RequestTimerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = "req_timer_" + str(uuid.uuid4())
        logger.info(f"request {str(request_id)} start")

        _start = time.monotonic()
        _start_response = None
        _response_end = None

        async def wrapped_send(message: Message):
            await send(message)
            if message["type"] == "http.response.start":
                _start_response = time.monotonic()
            if message["type"] == "http.response.body":
                if not message.get("more_body", False):
                    _response_end = time.monotonic()

        await self.app(scope, receive, wrapped_send)

        if _response_end is None:
            _response_end = time.monotonic()
        total_cost_s = f"{_response_end - _start:.6f}s"
        if _start_response:
            handle_cost_s = f"{_start_response - _start:.6f}s"
            transport_cost_s = f"{_start_response - _response_end:.6f}s"
        else:
            handle_cost_s = "none"
            transport_cost_s = "none"

        logger.info(
            f"request {str(request_id)} cost:\n"
            f"  total: {total_cost_s}\n"
            f"  handle request: {handle_cost_s}\n"
            f"  transport response body: {transport_cost_s}"
        )
