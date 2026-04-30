from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.mentor import ChatRequest, ChatResponse, MentorHistoryItem, SuggestedAction
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import mentor_service

router = APIRouter(prefix="/api/mentor", tags=["AI助手"])


@router.post("/chat", response_model=UnifiedResponse[ChatResponse])
async def chat(
    req: ChatRequest,
    thread_id: Optional[str] = Query(None, description="会话ID，用于多轮对话记忆"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息给AI助手（支持多轮对话记忆）"""
    data = await mentor_service.chat(db, current_user.id, req, thread_id)
    return UnifiedResponse(data=data)


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    thread_id: Optional[str] = Query(None, description="会话ID，用于多轮对话记忆"),
    current_user: User = Depends(get_current_user),
):
    """发送消息给AI助手 - SSE流式响应（支持多轮对话记忆）"""
    return StreamingResponse(
        mentor_service.chat_stream(current_user.id, req, thread_id),
        media_type="text/event-stream",
    )


@router.get("/history", response_model=UnifiedResponse[dict])
async def get_history(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史"""
    data = await mentor_service.get_history(db, current_user.id, page, pageSize)
    return UnifiedResponse(data=data)


@router.delete("/history", response_model=UnifiedResponse)
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空聊天历史"""
    await mentor_service.clear_history(db, current_user.id)
    return UnifiedResponse(message="聊天历史已清空")


@router.get("/suggested-actions", response_model=UnifiedResponse[list])
async def get_suggested_actions():
    """获取引导式提问列表"""
    data = mentor_service.get_suggested_actions()
    return UnifiedResponse(data=data)
