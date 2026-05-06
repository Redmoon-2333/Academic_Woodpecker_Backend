from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.resources import router as resources_router
from app.api.v1.mentor import router as mentor_router
from app.api.v1.study_plan import router as study_plan_router
from app.api.v1.learning import router as learning_router
from app.api.v1.today import router as today_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(analysis_router)
api_router.include_router(resources_router)
api_router.include_router(mentor_router)
api_router.include_router(study_plan_router)
api_router.include_router(learning_router)
api_router.include_router(today_router)
