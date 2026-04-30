from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class OverviewResponse(BaseModel):
    knowledgeRate: float = 0.0
    docCount: int = 0
    lastDiagnosis: Optional[str] = None
    growthRate: float = 0.0
    studyHours: str = "0小时"
    consecutiveDays: int = 0


class KnowledgeNode(BaseModel):
    id: int
    name: str
    status: str = "掌握"
    statusColor: str = "emerald"
    children: List["KnowledgeNode"] = []


KnowledgeNode.model_rebuild()


class WeakPoint(BaseModel):
    name: str
    severity: str = "high"


class RecommendedResource(BaseModel):
    id: int
    title: str
    type: str = "video"


class HistoricalScore(BaseModel):
    date: str
    score: float


class KnowledgeDetail(BaseModel):
    id: int
    name: str
    status: str = "薄弱"
    description: str = ""
    examFrequency: str = "中"
    difficultyLevel: str = "中"
    weakPoints: List[str] = []
    recommendedResources: List[RecommendedResource] = []
    historicalScores: List[HistoricalScore] = []
