import enum

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ResourceType(str, enum.Enum):
    video = "video"
    article = "article"
    course = "course"
    code = "code"


class Difficulty(str, enum.Enum):
    入门 = "入门"
    中级 = "中级"
    进阶 = "进阶"
    高级 = "高级"


class Resource(TimestampMixin, Base):
    __tablename__ = "resources"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    platform_color: Mapped[str] = mapped_column(String(20), nullable=True)
    type: Mapped[ResourceType] = mapped_column(SAEnum(ResourceType), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail: Mapped[str] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty), default=Difficulty.入门
    )
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)


class UserFavorite(TimestampMixin, Base):
    __tablename__ = "user_favorites"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("resources.id"), nullable=False
    )
