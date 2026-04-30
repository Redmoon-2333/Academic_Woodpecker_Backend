"""API routes for user learning records."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.learning import (
    CreateLearningRecordRequest,
    LearningRecordItem,
    LearningStats,
)
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import learning_service

router = APIRouter(prefix="/api/learning", tags=["学习记录"])


@router.post("/records", response_model=UnifiedResponse[LearningRecordItem])
async def create_learning_record(
    req: CreateLearningRecordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建一条学习活动记录"""
    data = await learning_service.create_record(db, current_user.id, req)
    return UnifiedResponse(data=data)


@router.get("/records", response_model=UnifiedResponse[dict])
async def list_learning_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    action: Optional[str] = Query(None, description="筛选动作: viewed / studied / completed"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学习记录列表（分页）"""
    data = await learning_service.get_records(db, current_user.id, page, page_size, action)
    return UnifiedResponse(data=data)


@router.get("/stats", response_model=UnifiedResponse[LearningStats])
async def get_learning_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学习统计数据（总计、今日、连续天数等）"""
    data = await learning_service.get_stats(db, current_user.id)
    return UnifiedResponse(data=data)
