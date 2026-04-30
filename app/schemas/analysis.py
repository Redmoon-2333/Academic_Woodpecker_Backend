from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class UploadResponse(BaseModel):
    fileId: str
    fileName: str
    fileSize: str
    uploadStatus: str = "success"
    previewUrl: Optional[str] = None


class Stage(BaseModel):
    name: str
    status: str = "pending"


class ProgressResponse(BaseModel):
    fileId: str
    status: str = "parsing"
    stage: str = "正在提取文本..."
    progress: int = 0
    stages: List[Stage] = []


class ExtractedKnowledge(BaseModel):
    name: str
    confidence: float = 0.0


class WeakPoint(BaseModel):
    name: str
    severity: str = "medium"


class OriginalFile(BaseModel):
    url: str
    name: str


class AnalysisResult(BaseModel):
    fileId: str
    originalFile: Optional[OriginalFile] = None
    extractedKnowledge: List[ExtractedKnowledge] = []
    weakPoints: List[WeakPoint] = []
    suggestions: List[str] = []
    summary: str = ""
    analyzedAt: Optional[str] = None


class HistoryRecord(BaseModel):
    id: int
    fileName: str
    uploadTime: Optional[str] = None
    status: str = "已分析"
    thumbnail: Optional[str] = None


class KnowledgePoint(BaseModel):
    name: str
    confidence: float = 0.0


class CorrectionRequest(BaseModel):
    extractedKnowledge: List[KnowledgePoint] = []
    weakPoints: List[WeakPoint] = []
    suggestions: List[str] = []
