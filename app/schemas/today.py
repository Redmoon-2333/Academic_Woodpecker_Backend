"""Pydantic schemas for today page endpoints."""
from typing import List, Optional
from pydantic import BaseModel, Field


# ==== Push ====

class TodayPushData(BaseModel):
    date: str = Field(description="今日日期 YYYY-MM-DD")
    weather: str = Field(description="天气（晴/多云/雨等）")
    suggestedStudyHours: int = Field(description="建议学习时长（小时）")
    status: str = Field(description="学习状态（最佳/良好/一般）")
    weeklyGrowthRate: float = Field(description="较上周增长率")


# ==== Recommendations ====

class RecommendationItem(BaseModel):
    type: str = Field(description="资源类型：video/exercise/article")
    typeLabel: str = Field(description="显示标签：视频/练习/文章")
    difficulty: str = Field(description="难度：入门/中级/进阶")
    title: str = Field(description="资源标题")
    platform: str = Field(description="来源平台")
    duration: Optional[str] = Field(None, description="时长或题数")
    reason: str = Field(description="推荐理由")
    url: str = Field(description="资源链接")
    thumbnail: Optional[str] = Field(None, description="缩略图 URL")


class TodayRecommendationsData(BaseModel):
    recommendations: List[RecommendationItem] = []


# ==== Progress ====

class WeeklyTrendItem(BaseModel):
    day: str = Field(description="星期简写 Mon/Tue/...")
    hours: float = Field(description="当天学习时长")
    isToday: bool = Field(description="是否为今天")


class TodayProgressData(BaseModel):
    weeklyStudyHours: float = Field(description="本周总学习时长（小时）")
    weeklyGrowthRate: float = Field(description="较上周增长率")
    knowledgeRate: float = Field(description="当前知识点掌握率")
    knowledgeGrowthRate: float = Field(description="掌握率较上周提升")
    weeklyTrend: List[WeeklyTrendItem] = Field(default_factory=list)


# ==== Goals ====

class TodayGoalItem(BaseModel):
    id: str = Field(description="目标ID")
    title: str = Field(description="任务标题")
    estimatedMinutes: int = Field(description="预计耗时（分钟）")
    completed: bool = Field(description="是否完成")


class TodayGoalsData(BaseModel):
    planId: Optional[int] = None
    todayGoals: List[TodayGoalItem] = []
    studyTips: List[str] = []


class GoalUpdateRequest(BaseModel):
    completed: bool = True


# ==== Start Study ====

class StudySessionData(BaseModel):
    sessionId: str = Field(description="学习会话ID")
