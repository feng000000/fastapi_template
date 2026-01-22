from fastapi.responses import JSONResponse


class SuccessResponse(JSONResponse):
    def __init__(self, data: dict | list | None = None) -> None:
        super().__init__(
            {
                "code": 200,
                "status": "success",
                **({} if data is None else {"data": data}),
            }
        )


class ErrorResponse(JSONResponse):
    def __init__(
        self,
        code: int = 500,
        msg: str = "internal server error",
    ) -> None:
        super().__init__(
            {
                "code": code,
                "status": "error",
                "data": {"message": msg},
            }
        )


class ValidationErrorResponse(ErrorResponse):
    def __init__(self) -> None:
        super().__init__(code=400, msg="validation error")
