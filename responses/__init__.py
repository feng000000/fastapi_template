from typing import Literal

from fastapi.responses import JSONResponse


class BaseResponse(JSONResponse):
    def __init__(
        self,
        status_code: int,
        status: Literal["success", "error"],
        data: list | dict | None = None,
        msg: str | None = None,
    ) -> None:
        content = {
            "status": status,
            **({"data": data} if data else {}),
            **({"msg": msg} if msg else {}),
        }
        super().__init__(content=content, status_code=status_code)


class SuccessResponse(BaseResponse):
    def __init__(self, data: list | dict) -> None:
        super().__init__(
            status_code=200,
            status="success",
            data=data,
        )


class ErrorResponse(BaseResponse):
    def __init__(self, msg: str, status_code: int = 500) -> None:
        super().__init__(
            status_code=status_code,
            status="error",
            msg=msg,
        )


class ValidationErrorResponse(ErrorResponse):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            msg="Validation error",
        )


class InternalErrorResponse(ErrorResponse):
    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            msg="Internal server error",
        )
