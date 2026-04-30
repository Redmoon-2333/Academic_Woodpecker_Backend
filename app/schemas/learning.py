"""Pydantic schemas for learning records."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CreateLearningRecordRequest(BaseModel):
    """Request to create a learning activity record."""
    resource_id: Optional[int] = Field(None, description="关联资源ID")
    action: str = Field(default="viewed", description="动作: viewed / studied / completed")
    duration_seconds: Optional[int] = Field(None, description="学习时长(秒)", ge=0)


class LearningRecordItem(BaseModel):
    """Single learning record in response."""
    id: int
    resource_id: Optional[int] = None
    resource_title: Optional[str] = None
    action: str
    content: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_at: str


class LearningStats(BaseModel):
    """Aggregated learning statistics."""
    total_viewed: int = 0
    total_studied: int = 0
    total_completed: int = 0
    total_duration_minutes: float = 0.0
    today_records: int = 0
    streak_days: int = 0
