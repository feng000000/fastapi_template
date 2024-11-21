from fastapi import APIRouter

from . import helloworld

router = APIRouter()

# TODO: include specific router
router.include_router(helloworld.router)
