import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import ValidationException

from responses import ErrorResponse, ValidationErrorResponse

logger = logging.getLogger(__name__)


def register_exception_handler(app: FastAPI):
    def _register_handler(
        exc_type: type[Exception],
        resp_type: type[ErrorResponse],
        resp_message: str,
    ):
        def _handler(_: Request, exc: Exception):
            if isinstance(exc, ValidationException):
                logger.error(f"validation error: {type(exc), exc}")
            else:
                logger.error(
                    f"catch exception\ntraceback: {traceback.format_exc()}"
                )
            return resp_type(msg=resp_message)

        app.add_exception_handler(exc_type, _handler)

    _register_handler(
        exc_type=ValidationException,
        resp_type=ValidationErrorResponse,
        resp_message="validation error",
    )
    _register_handler(
        exc_type=Exception,
        resp_type=ErrorResponse,
        resp_message="internal server error",
    )
