from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")


class UnifiedResponse(BaseModel, Generic[DataT]):
    code: int = 200
    message: str = "success"
    data: Optional[DataT] = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    total: int = 0
    page: int = 1
    page_size: int = 10
    records: List[DataT] = []


class ErrorResponse(BaseModel):
    code: int = 400
    message: str = "error"
    data: Any = None
