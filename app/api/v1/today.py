"""API routes for today page (今日推送)."""

from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.today import (
    TodayPushData,
    TodayRecommendationsData,
    TodayProgressData,
    TodayGoalsData,
    GoalUpdateRequest,
    StudySessionData,
)
from app.api.deps import get_current_user
from app.models.user import User
from app.services import today_service

router = APIRouter(prefix="/api/today", tags=["今日推送"])


@router.get("/push", response_model=UnifiedResponse[TodayPushData])
async def get_push(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今日推送头部信息（天气、建议时长、状态、增长率）"""
    data = await today_service.get_push(db, current_user.id)
    return UnifiedResponse(data=data)


@router.get("/recommendations", response_model=UnifiedResponse[TodayRecommendationsData])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取个性化推荐内容（按类型分类）"""
    data = await today_service.get_recommendations(db, current_user.id)
    return UnifiedResponse(data=data)


@router.get("/progress", response_model=UnifiedResponse[TodayProgressData])
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取本周学习进度和趋势数据"""
    data = await today_service.get_progress(db, current_user.id)
    return UnifiedResponse(data=data)


@router.get("/goals", response_model=UnifiedResponse[TodayGoalsData])
async def get_today_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取今日学习目标（适配自当前学习计划）"""
    data = await today_service.get_today_goals(db, current_user.id)
    return UnifiedResponse(data=data)


@router.put("/goals/{goal_id}", response_model=UnifiedResponse)
async def update_goal(
    goal_id: str = Path(..., description="目标ID，格式 goal_{planId}_{taskIndex}"),
    req: GoalUpdateRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新今日目标的完成状态"""
    if req is None:
        req = GoalUpdateRequest()
    ok = await today_service.update_goal_completed(db, current_user.id, goal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="目标不存在或无权操作")
    return UnifiedResponse(message="目标状态已更新")


@router.post("/start-study", response_model=UnifiedResponse[StudySessionData])
async def start_study(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录用户开始学习，返回会话ID"""
    data = await today_service.start_study(db, current_user.id)
    return UnifiedResponse(data=data)
