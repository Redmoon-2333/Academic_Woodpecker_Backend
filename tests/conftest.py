import pytest
import asyncio
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Import all models so SQLAlchemy knows about all tables
import app.models  # noqa: F401
from app.database import get_db
from app.models.base import Base
from app.main import app
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.knowledge import KnowledgePoint
from app.models.resource import Resource


# In-memory test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def pytest_configure(config):
    """Enable asyncio mode for all tests."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestAsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestAsyncSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        username="testuser",
        password_hash=get_password_hash("test123456"),
        nickname="测试用户",
        email="test@example.com",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def seed_knowledge(db_session: AsyncSession):
    subjects = [
        KnowledgePoint(
            id=100, name="高等数学", parent_id=None, subject="高等数学"
        ),
        KnowledgePoint(
            id=101, name="微积分", parent_id=100, subject="高等数学"
        ),
        KnowledgePoint(
            id=102, name="线性代数", parent_id=100, subject="高等数学"
        ),
        KnowledgePoint(
            id=200, name="大学物理", parent_id=None, subject="大学物理"
        ),
    ]
    for kp in subjects:
        db_session.add(kp)
    await db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def seed_resources(db_session: AsyncSession):
    resources = [
        Resource(
            id=100,
            title="测试视频",
            platform="Bilibili",
            type="video",
            url="https://test.com",
            rating=4.5,
            difficulty="入门",
            tags=["测试"],
        ),
        Resource(
            id=101,
            title="测试文章",
            platform="知乎",
            type="article",
            url="https://test.com",
            rating=4.0,
            difficulty="中级",
            tags=["测试"],
        ),
    ]
    for r in resources:
        db_session.add(r)
    await db_session.commit()
