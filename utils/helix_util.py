from __future__ import annotations

import logging
from uuid import UUID

import httpx
from pydantic import BaseModel, field_validator

from config import config

logger = logging.getLogger(__name__)

_USER_INFO_ENDPOINT = f"{config.HELIXLIFE_BASE_URL}/api/v1/user/users/profile"
_SUCCESS_CODE = 20000


class HelixlifeUser(BaseModel):
    uuid: UUID
    avatar: str
    nickname: str
    mobile: str
    raw: dict = {}

    @field_validator("avatar", mode="before")
    @classmethod
    def avatar_validator(cls, v: str) -> str:
        if len(v) <= 100:
            return v
        return ""

    @classmethod
    def from_token(cls, token: str) -> HelixlifeUser:
        headers = {"source": "api", "Authorization": f"Bearer {token}"}
        response = httpx.get(_USER_INFO_ENDPOINT, headers=headers)
        raw_info = response.json()

        if raw_info.get("code") != _SUCCESS_CODE:
            logger.error(f"get helix user info failed: {raw_info}")
            raise Exception(
                raw_info.get("message", "get helix user info failed")
            )

        data = raw_info.get("data", {})
        return cls(**data, raw=raw_info)
