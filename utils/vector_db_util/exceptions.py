class VectorDBError(Exception):
    code: int
    detail: str

    def __init__(self, detail, code=0):
        self.code = code
        self.detail = detail
