import logging

from fastapi import APIRouter

from responses import SuccessResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/")
async def hello_world():
    return SuccessResponse(data=[])
