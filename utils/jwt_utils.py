from collections.abc import Sequence
from datetime import datetime, timedelta

import jwt
from pydantic import BaseModel, Field

from config import config


class JWTPayload(BaseModel):
    payload: dict

    exp: int = Field(
        default_factory=(
            lambda: int((datetime.now() + timedelta(hours=3)).timestamp())
        ),
        description="Expiration Time, 过期时间",
    )
    nbf: int | None = Field(default=None, description="Not Before; 生效时间戳")
    iat: int | None = Field(default=None, description="Issued At; 签发时间戳")
    jti: str | None = Field(
        default=None, description="JWT ID; 唯一标识, 避免重放"
    )
    sub: str | None = Field(
        default=None, description="Subject; token 代表的实体"
    )
    aud: str | Sequence[str] | None = Field(
        default=None,
        description="Audience; Token 的受众, 例如 user",
    )
    iss: str | None = Field(default=None, description="Issuer; 签发者")

    def model_dump(self, *args, **kw):
        data = super().model_dump(
            *args,
            exclude={"payload"},
            exclude_none=True,
            **kw,
        )
        return {**data, **self.payload}


def verify_token(
    token: str,
    secret_key: str = config.SECRET_KEY,
    algorithms: Sequence[str] = ("HS256", "RS256"),
    audiences: str | None = None,
) -> dict | None:
    try:
        decoded_payload = jwt.decode(
            jwt=token,
            key=secret_key,
            algorithms=algorithms,
            audience=audiences,
        )
    except Exception:
        return None

    return decoded_payload


def generate_token(
    payload: JWTPayload,
    secret_key: str = config.SECRET_KEY,
    algorithm: str = "HS256",  # RS256 for Asymmetric JWT
) -> str:
    return jwt.encode(payload.model_dump(), secret_key, algorithm=algorithm)


if __name__ == "__main__":
    with open("./private_rsa.pem") as f:
        private = f.read()
    with open("./public_rsa.pem") as f:
        public = f.read()

    res = generate_token(
        payload=JWTPayload(payload={"data": {"inner_data": 123}}),
        secret_key=private,
        algorithm="RS256",
    )
    print("jwt:", res)

    res = verify_token(
        token=res,
        secret_key=public,
        algorithms=("RS256"),
    )
    print("verify res:", res)
