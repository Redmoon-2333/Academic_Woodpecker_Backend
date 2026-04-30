from typing import List
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.dashboard import OverviewResponse, KnowledgeDetail
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["学情仪表盘"])


@router.get("/overview", response_model=UnifiedResponse[OverviewResponse])
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取学情概览"""
    data = await dashboard_service.get_overview(db, current_user.id)
    return UnifiedResponse(data=data)


@router.get("/knowledge-graph", response_model=UnifiedResponse[dict])
async def get_knowledge_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识图谱数据"""
    data = await dashboard_service.get_knowledge_graph(db, current_user.id)
    return UnifiedResponse(data={"nodes": data})


@router.get("/knowledge/{knowledge_id}", response_model=UnifiedResponse[KnowledgeDetail])
async def get_knowledge_detail(
    knowledge_id: int = Path(..., description="知识点ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取薄弱知识点详情"""
    data = await dashboard_service.get_knowledge_detail(
        db, current_user.id, knowledge_id
    )
    return UnifiedResponse(data=data)
