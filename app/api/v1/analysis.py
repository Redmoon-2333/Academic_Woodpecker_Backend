from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analysis import (
    UploadResponse,
    ProgressResponse,
    AnalysisResult,
    CorrectionRequest,
)
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["数据上传与解析"])


@router.post("/upload", response_model=UnifiedResponse[UploadResponse])
async def upload_file(
    file: UploadFile = File(...),
    fileType: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文件进行分析"""
    data = await analysis_service.upload_file(db, current_user.id, file, fileType)
    return UnifiedResponse(data=data)


@router.get("/progress/{file_id}", response_model=UnifiedResponse[ProgressResponse])
async def get_progress(
    file_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解析进度"""
    data = await analysis_service.get_progress(db, file_id)
    return UnifiedResponse(data=data)


@router.get("/result/{file_id}", response_model=UnifiedResponse[AnalysisResult])
async def get_result(
    file_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解析结果"""
    data = await analysis_service.get_result(db, file_id)
    return UnifiedResponse(data=data)


@router.get("/history", response_model=UnifiedResponse[dict])
async def get_history(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取历史分析记录"""
    data = await analysis_service.get_history(db, current_user.id, page, pageSize)
    return UnifiedResponse(data=data)


@router.put("/result/{file_id}", response_model=UnifiedResponse)
async def correct_result(
    correction: CorrectionRequest,
    file_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动校正解析结果"""
    await analysis_service.correct_result(db, current_user.id, file_id, correction)
    return UnifiedResponse(message="校正成功")