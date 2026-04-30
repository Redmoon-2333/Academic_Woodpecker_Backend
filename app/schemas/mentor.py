from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, List[str]]] = None
    suggestedAction: Optional[str] = None


class RelatedResource(BaseModel):
    id: int
    title: str
    type: str = "video"


class ChatResponse(BaseModel):
    messageId: str
    content: str
    timestamp: str = ""
    threadId: Optional[str] = None  # 会话ID，用于多轮对话记忆
    suggestedQuestions: List[str] = []
    relatedResources: List[RelatedResource] = []


class MentorHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str = ""


class SuggestedAction(BaseModel):
    id: int
    text: str
    icon: str = "plan"
