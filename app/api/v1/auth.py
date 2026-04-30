from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.schemas.common import UnifiedResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证模块"])


@router.post("/login", response_model=UnifiedResponse[TokenResponse])
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    token, user = await auth_service.login(db, req.username, req.password)
    user_info = await auth_service.get_current_user_info(user)
    return UnifiedResponse(data=TokenResponse(token=token, userInfo=user_info))


@router.post("/register", response_model=UnifiedResponse[UserInfo])
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    user = await auth_service.register(db, req)
    user_info = await auth_service.get_current_user_info(user)
    return UnifiedResponse(data=user_info)


@router.get("/current-user", response_model=UnifiedResponse[UserInfo])
async def current_user(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    user_info = await auth_service.get_current_user_info(current_user)
    return UnifiedResponse(data=user_info)
