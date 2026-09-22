from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_column

DIFFICULTY = ("low", "mid", "high", "top")
EXAM_STATUS = ("draft", "confirmed")
FORM_TYPE = ("odd", "even")
ATTEMPT_SOURCE = ("omr", "manual")
OMR_SCAN_STATUS = ("read", "needs_review", "applied")


class Exam(Base):
    __tablename__ = "exam"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("class.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    exam_date: Mapped[date | None] = mapped_column(Date)
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_file.id"))
    question_count: Mapped[int | None] = mapped_column()
    max_score: Mapped[int | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        enum_column("exam_status", *EXAM_STATUS), default="draft"
    )
    answer_key_odd: Mapped[list | None] = mapped_column(JSON)
    answer_key_even: Mapped[list | None] = mapped_column(JSON)


class ExamQuestion(Base):
    __tablename__ = "exam_question"
    __table_args__ = (UniqueConstraint("exam_id", "no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), index=True)
    no: Mapped[int] = mapped_column()
    unit: Mapped[str | None] = mapped_column(String(200))
    sub_type: Mapped[str | None] = mapped_column(String(200))
    difficulty: Mapped[str | None] = mapped_column(enum_column("difficulty", *DIFFICULTY))
    rationale: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int | None] = mapped_column()
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))


class ExamAttempt(Base):
    __tablename__ = "exam_attempt"
    __table_args__ = (UniqueConstraint("exam_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    form_type: Mapped[str | None] = mapped_column(enum_column("form_type", *FORM_TYPE))
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    source: Mapped[str] = mapped_column(enum_column("attempt_source", *ATTEMPT_SOURCE))
    flags: Mapped[list | None] = mapped_column(JSON)


class ExamAnswer(Base):
    __tablename__ = "exam_answer"
    __table_args__ = (UniqueConstraint("attempt_id", "question_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempt.id"), index=True)
    question_no: Mapped[int] = mapped_column()
    raw_value: Mapped[str | None] = mapped_column(String(20))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)


class OmrScan(Base):
    __tablename__ = "omr_scan"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), index=True)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_file.id"))
    page_no: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(
        enum_column("omr_scan_status", *OMR_SCAN_STATUS), default="read"
    )
    matched_student_id: Mapped[int | None] = mapped_column(ForeignKey("student.id"))
    read_payload: Mapped[dict | None] = mapped_column(JSON)
    flags: Mapped[list | None] = mapped_column(JSON)


class LabelCorrection(Base):
    """OMR·문항 분석의 교정 이력. 향후 학습 데이터로 재사용한다(FR-35)."""

    __tablename__ = "label_correction"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    source_ref: Mapped[str] = mapped_column(String(200))
    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)
    asset_ref: Mapped[str | None] = mapped_column(String(500))
    corrected_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
