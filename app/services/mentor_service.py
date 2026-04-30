from datetime import datetime
from typing import List, Optional, Dict, AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models.chat_message import ChatMessage, MessageRole
from app.schemas.mentor import (
    ChatRequest, ChatResponse, RelatedResource,
    MentorHistoryItem, SuggestedAction,
)
from app.agents.mentor_agent import chat_with_mentor, chat_with_mentor_stream


async def chat(
    db: AsyncSession,
    user_id: int,
    req: ChatRequest,
    thread_id: Optional[str] = None,
) -> ChatResponse:
    """Process a chat message, get AI response, and save to history."""
    # Save user message
    user_msg = ChatMessage(
        user_id=user_id,
        role=MessageRole.user,
        content=req.message,
        context=req.context,
    )
    db.add(user_msg)
    await db.commit()

    # Get AI response from mentor agent (with memory via thread_id)
    try:
        ai_content = await chat_with_mentor(req.message, req.context, thread_id)
    except Exception as e:
        ai_content = f"抱歉，我暂时无法回答这个问题。请稍后再试。"

    # Save AI response
    ai_msg = ChatMessage(
        user_id=user_id,
        role=MessageRole.assistant,
        content=ai_content,
        context=req.context,
    )
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    timestamp = (
        ai_msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        if ai_msg.created_at
        else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    return ChatResponse(
        messageId=str(ai_msg.id),
        content=ai_content,
        timestamp=timestamp,
        threadId=thread_id,
        suggestedQuestions=[
            "这个知识点还有哪些常见题型？",
            "帮我对比一下这两个概念的区别",
            "给我出一道综合练习题",
            "推荐一些进阶学习资源",
        ],
        relatedResources=[
            RelatedResource(id=1, title="相关学习资料", type="video"),
        ],
    )


async def chat_stream(
    user_id: int,
    req: ChatRequest,
    thread_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream AI chat response token by token.

    Args:
        user_id: The current user's ID.
        req: The chat request containing message and optional context.
        thread_id: Conversation thread ID for multi-turn memory.

    Yields:
        Content chunks from the AI response as they arrive.
    """
    async for chunk in chat_with_mentor_stream(req.message, req.context, thread_id):
        yield chunk


async def get_history(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """Get paginated chat history."""
    result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user_id)
    )
    total = result.scalar() or 0

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(desc(ChatMessage.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    messages = result.scalars().all()

    # Reverse to show chronological order
    messages = list(reversed(messages))

    items = [
        MentorHistoryItem(
            id=str(msg.id),
            role=msg.role.value if hasattr(msg.role, "value") else msg.role,
            content=msg.content,
            timestamp=(
                msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if msg.created_at
                else ""
            ),
        )
        for msg in messages
    ]

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "messages": [item.model_dump() for item in items],
    }


async def clear_history(db: AsyncSession, user_id: int):
    """Clear all chat messages for a user."""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == user_id)
    )
    messages = result.scalars().all()
    for msg in messages:
        await db.delete(msg)
    await db.commit()


def get_suggested_actions() -> List[dict]:
    """Get preset suggested action buttons."""
    return [
        {"id": 1, "text": "帮我制定一个复习计划", "icon": "plan"},
        {"id": 2, "text": "总结我最近的易错类型", "icon": "chart"},
        {"id": 3, "text": "解释一下贝叶斯定理", "icon": "book"},
        {"id": 4, "text": "推荐一些练习题", "icon": "practice"},
    ]
