import enum

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class FileType(str, enum.Enum):
    成绩单 = "成绩单"
    笔记 = "笔记"
    试卷 = "试卷"


class DocStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(SAEnum(FileType), nullable=True)
    status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus), default=DocStatus.pending
    )
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
