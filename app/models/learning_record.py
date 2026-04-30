"""User learning record model - tracks resource browsing and study activities."""
import enum
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class LearningAction(enum.Enum):
    viewed = "viewed"
    studied = "studied"
    completed = "completed"


class UserLearningRecord(Base):
    __tablename__ = "user_learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("resources.id"), nullable=True)
    action: Mapped[LearningAction] = mapped_column(Enum(LearningAction), default=LearningAction.viewed)
    content: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
