from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class ResourceItem(BaseModel):
    id: int
    title: str
    platform: str
    platformColor: Optional[str] = None
    type: str = "video"
    rating: float = 0.0
    reason: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    difficulty: str = "入门"
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    aiRecommend: bool = True


class ResourceDetail(BaseModel):
    id: int
    title: str
    platform: str
    type: str = "video"
    rating: float = 0.0
    reason: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    difficulty: str = "入门"
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    viewCount: int = 0
    createdAt: Optional[str] = None


class SearchQuery(BaseModel):
    keyword: str = ""
    page: int = 1
    pageSize: int = 10


class FavoriteResponse(BaseModel):
    favorited: bool = True
    resourceId: int
