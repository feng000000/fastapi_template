import logging
import traceback
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import ValidationException

from responses import ErrorResponse, ValidationErrorResponse

logger = logging.getLogger(__name__)


def register_exception_handler(app: FastAPI):
    def _register_handler[**P, R: ErrorResponse](
        exc_type: type[Exception],
        resp_type: Callable[P, R],
        *arg: P.args,
        **kw: P.kwargs,
    ):
        def _handler(_: Request, exc: Exception):
            if isinstance(exc, ValidationException):
                logger.error(f"validation error: {type(exc), exc}")
            else:
                logger.error(
                    f"catch exception\ntraceback: {traceback.format_exc()}"
                )
            return resp_type(*arg, **kw)

        app.add_exception_handler(exc_type, _handler)

    _register_handler(
        exc_type=ValidationException,
        resp_type=ValidationErrorResponse,
    )
    _register_handler(
        exc_type=Exception,
        resp_type=ErrorResponse,
        msg="internal server error",
    )
