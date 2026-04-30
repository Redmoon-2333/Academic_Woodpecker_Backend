from app.schemas.common import UnifiedResponse, PaginatedResponse, ErrorResponse
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.schemas.dashboard import OverviewResponse, KnowledgeNode, KnowledgeDetail
from app.schemas.analysis import UploadResponse, ProgressResponse, AnalysisResult, HistoryRecord, CorrectionRequest
from app.schemas.resource import ResourceItem, ResourceDetail, SearchQuery, FavoriteResponse
from app.schemas.mentor import ChatRequest, ChatResponse, MentorHistoryItem, SuggestedAction
from app.schemas.study_plan import GeneratePlanRequest, PlanResponse, ProgressUpdateRequest
from app.schemas.learning import CreateLearningRecordRequest, LearningRecordItem, LearningStats
