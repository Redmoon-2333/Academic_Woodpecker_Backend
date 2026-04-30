from sqlalchemy import ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StudyPlan(TimestampMixin, Base):
    __tablename__ = "study_plans"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)
