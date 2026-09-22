from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_column

ATTENDANCE_STATUS = ("unchecked", "present", "late", "absent", "early_leave")
HOMEWORK_GRADE = ("A+", "A", "B", "C", "D", "F")


class ClassSession(Base):
    __tablename__ = "class_session"
    __table_args__ = (UniqueConstraint("class_id", "session_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date)
    homework: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))
    teacher_note: Mapped[str | None] = mapped_column(Text)
    test_name: Mapped[str | None] = mapped_column(String(100))
    test_max_score: Mapped[int | None] = mapped_column()
    attendance_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attendance_confirmed_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))


class ClassSessionProgress(Base):
    __tablename__ = "class_session_progress"
    __table_args__ = (UniqueConstraint("session_id", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_session.id"), index=True)
    period: Mapped[int] = mapped_column()
    content: Mapped[str | None] = mapped_column(Text)


class StudentDailyRecord(Base):
    __tablename__ = "student_daily_record"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_session.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    attendance_status: Mapped[str] = mapped_column(
        enum_column("attendance_status", *ATTENDANCE_STATUS), default="unchecked"
    )
    attendance_reason: Mapped[str | None] = mapped_column(String(200))
    homework_grade: Mapped[str | None] = mapped_column(
        enum_column("homework_grade", *HOMEWORK_GRADE)
    )
    recheck_result: Mapped[str | None] = mapped_column(
        enum_column("recheck_result", "pass", "fail")
    )
    test_score_num: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    test_score_text: Mapped[str | None] = mapped_column(String(200))
