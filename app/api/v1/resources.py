from typing import Optional
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.resource import ResourceDetail, FavoriteResponse
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import resource_service

router = APIRouter(prefix="/api/resources", tags=["资源推荐"])


@router.get("", response_model=UnifiedResponse[dict])
async def list_resources(
    type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐资源列表"""
    data = await resource_service.get_resources(db, type, difficulty, tag, page, pageSize)
    return UnifiedResponse(data=data)


@router.get("/search", response_model=UnifiedResponse[dict])
async def search_resources(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """搜索资源"""
    data = await resource_service.search_resources(db, keyword, page, pageSize)
    return UnifiedResponse(data=data)


@router.get("/favorites", response_model=UnifiedResponse[dict])
async def get_favorites(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的收藏"""
    data = await resource_service.get_favorites(db, current_user.id, page, pageSize)
    return UnifiedResponse(data=data)


@router.get("/{resource_id}", response_model=UnifiedResponse[ResourceDetail])
async def get_resource_detail(
    resource_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """获取资源详情"""
    data = await resource_service.get_resource_detail(db, resource_id)
    return UnifiedResponse(data=data)


@router.post("/{resource_id}/favorite", response_model=UnifiedResponse[FavoriteResponse])
async def toggle_favorite(
    resource_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """收藏/取消收藏资源"""
    data = await resource_service.toggle_favorite(db, current_user.id, resource_id)
    return UnifiedResponse(data=data)
