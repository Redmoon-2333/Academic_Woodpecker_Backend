from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    nickname: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = None
    studentId: Optional[str] = None


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    avatar: Optional[str] = None
    role: str = "student"


class TokenResponse(BaseModel):
    token: str
    userInfo: UserInfo
