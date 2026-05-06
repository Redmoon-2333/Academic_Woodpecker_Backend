from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.study_plan import GeneratePlanRequest, PlanResponse, ProgressUpdateRequest
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import study_plan_service

router = APIRouter(prefix="/api/plan", tags=["学习计划"])


@router.post("/generate", response_model=UnifiedResponse[PlanResponse])
async def generate_plan(
    req: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成学习计划"""
    data = await study_plan_service.generate_plan(db, current_user.id, req)
    return UnifiedResponse(data=data)


@router.get("/current", response_model=UnifiedResponse)
async def get_current_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前学习计划（今日目标适配版）"""
    data = await study_plan_service.get_current_plan_today(db, current_user.id)
    return UnifiedResponse(data=data)


@router.put("/{plan_id}/progress", response_model=UnifiedResponse)
async def update_progress(
    req: ProgressUpdateRequest,
    plan_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新学习计划进度"""
    await study_plan_service.update_progress(db, current_user.id, plan_id, req)
    return UnifiedResponse(message="进度已更新")
