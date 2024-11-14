from fastapi import APIRouter

from . import helloworld

router = APIRouter()

# TODO: include router
router.include_router(helloworld.router)
