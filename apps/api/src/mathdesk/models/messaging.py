from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_column
from .daily import HOMEWORK_GRADE


class GradeComment(Base):
    __tablename__ = "grade_comment"
    __table_args__ = (UniqueConstraint("campus_id", "grade"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    grade: Mapped[str] = mapped_column(enum_column("homework_grade", *HOMEWORK_GRADE))
    comment_text: Mapped[str] = mapped_column(Text)


class MessageTemplate(Base):
    __tablename__ = "message_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    body: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class MessageLog(Base):
    __tablename__ = "message_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("student.id"), index=True)
    recipient_type: Mapped[str] = mapped_column(
        enum_column("recipient_type", "student", "guardian")
    )
    recipient_phone: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(
        enum_column("message_channel", "sms", "lms", "mms", "alimtalk")
    )
    status: Mapped[str] = mapped_column(
        enum_column("message_status", "test", "queued", "sent", "failed", "fallback_sent")
    )
    body_snapshot: Mapped[str] = mapped_column(Text)
    cost_unit: Mapped[int | None] = mapped_column()
    is_test: Mapped[bool] = mapped_column(Boolean, default=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    result_code: Mapped[str | None] = mapped_column(String(50))
    error: Mapped[str | None] = mapped_column(Text)
