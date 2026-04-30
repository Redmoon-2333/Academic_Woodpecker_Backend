from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserInfo
from app.core.security import get_password_hash, verify_password, create_access_token
from fastapi import HTTPException, status


async def register(db: AsyncSession, req: RegisterRequest) -> User:
    """Register a new user. Raises 400 if username exists."""
    result = await db.execute(select(User).where(User.username == req.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        password_hash=get_password_hash(req.password),
        nickname=req.nickname,
        email=req.email,
        student_id=req.studentId,
        role="student",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login(db: AsyncSession, username: str, password: str) -> tuple[str, User]:
    """Authenticate user and return JWT token + user. Raises 401 on failure."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(data={"sub": str(user.id)})
    return token, user


async def get_current_user_info(user: User) -> UserInfo:
    """Map User model to UserInfo schema."""
    return UserInfo(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        role=user.role.value if hasattr(user.role, 'value') else user.role,
    )
