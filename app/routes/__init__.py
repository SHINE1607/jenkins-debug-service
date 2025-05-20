from fastapi import APIRouter
from app.routes.result import router as result_router

router = APIRouter(prefix="/v1")

router.include_router(result_router)
