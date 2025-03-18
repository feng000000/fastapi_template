from datetime import datetime, timedelta

import jwt
from pydantic import BaseModel

from config import config


class JWTPayload(BaseModel):
    aud: str = "user"
    iss: str = "api-backend"
    exp: int = int((datetime.now() + timedelta(hours=3)).timestamp())
    sub: str | None = None
    iat: int | None = None
    nbf: int | None = None

    custom: dict = {}

    def model_dump(self, *args, **kw):
        data = super().model_dump(*args, **kw)
        custom_field = data.pop("custom_field", {})
        return {**data, **custom_field}


def verify_token(
    authorization: str,
    secret_key=config.SECRET_KEY,
) -> dict | None:
    try:
        token = authorization.split(" ")[1]
        decoded_payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except Exception:
        return None

    return decoded_payload


def generate_token(
    payload: JWTPayload,
    secret_key=config.SECRET_KEY,
):
    return jwt.encode(payload.model_dump(), secret_key, algorithm="HS256")
