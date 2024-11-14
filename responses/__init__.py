from fastapi.responses import JSONResponse


class HelloResponse(JSONResponse):
    def __init__(self):
        super().__init__(
            status_code=200,
            content={
                "code": 3020,
                "msg": "hello",
            },
        )
