import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgeStatus(str, enum.Enum):
    掌握 = "掌握"
    预警 = "预警"
    薄弱 = "薄弱"


class ExamFrequency(str, enum.Enum):
    高 = "高"
    中 = "中"
    低 = "低"


class KnowledgePoint(TimestampMixin, Base):
    __tablename__ = "knowledge_points"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[KnowledgeStatus] = mapped_column(
        SAEnum(KnowledgeStatus), default=KnowledgeStatus.掌握
    )
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    exam_frequency: Mapped[ExamFrequency] = mapped_column(
        SAEnum(ExamFrequency), default=ExamFrequency.中
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)


class UserKnowledge(TimestampMixin, Base):
    __tablename__ = "user_knowledge"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    exam_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
