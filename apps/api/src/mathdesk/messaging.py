from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .daily import _session_for_write, _enrolled_students
from .db import get_session
from .models import (
    AppUser,
    Campus,
    ClassSession,
    ClassSessionProgress,
    GradeComment,
    Klass,
    Student,
    StudentDailyRecord,
)
from .models.daily import HOMEWORK_GRADE
from .scope import CurrentScope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/messages", tags=["messages"])

WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")
ATTENDANCE_LABEL = {
    "present": "출석",
    "late": "지각",
    "absent": "결석",
    "early_leave": "조퇴",
}


class MessageContext(BaseModel):
    """본문 렌더에 필요한 값만 담는다. 저장하지 않고 요청마다 만든다(FR-18)."""

    student_name: str
    campus_name: str
    teacher_name: str
    session_date: date
    attendance: str | None = None
    progress: list[tuple[int, str | None]] = Field(default_factory=list)
    homework_grade: str | None = None
    grade_comment: str | None = None
    test_name: str | None = None
    test_score: str | None = None
    class_average: float | None = None
    homework: str | None = None
    video_url: str | None = None


def render_daily_message(context: MessageContext) -> str:
    day = context.session_date
    blocks: list[str] = [
        f"**{context.student_name}학생 학습피드백**\n"
        f"{context.campus_name} {context.teacher_name}T입니다.\n"
        f"{day.month}월 {day.day}일({WEEKDAYS[day.weekday()]}) 수업 내용 및 과제피드백 안내드립니다."
    ]

    attendance = ATTENDANCE_LABEL.get(context.attendance or "")
    if attendance:
        blocks.append(f"■ 출결: {attendance}")

    lines = [f"[{period}교시] {content}" for period, content in context.progress if content]
    if lines:
        blocks.append("■ 수업진도\n" + "\n".join(lines))

    if context.homework_grade:
        feedback = f"■ 과제피드백: {context.homework_grade}"
        if context.grade_comment:
            feedback += f"\n{context.grade_comment}"
        blocks.append(feedback)

    if context.test_name and context.test_score is not None:
        test = f"■ 테스트: {context.test_name}\n   학생점수: {context.test_score}점"
        if context.class_average is not None:
            test += f"\n   반평균: {context.class_average}점"
        blocks.append(test)

    if context.homework:
        blocks.append(f"■ 오늘의 과제\n{context.homework}")

    if context.video_url:
        blocks.append(f"■ 수업 영상 링크\n{context.video_url}")

    return "\n\n".join(blocks)


class GradeCommentIn(BaseModel):
    grade: str = Field(pattern="^(%s)$" % "|".join(g.replace("+", r"\+") for g in HOMEWORK_GRADE))
    comment_text: str


class GradeCommentsIn(BaseModel):
    comments: list[GradeCommentIn]


class PreviewOut(BaseModel):
    body: str


def _format_score(value: Decimal | None, text: str | None) -> str | None:
    if value is not None:
        return str(int(value)) if value == value.to_integral_value() else str(value)
    return text


@router.get("/grade-comments")
async def list_grade_comments(scope: CurrentScope, session: Db) -> list[GradeCommentIn]:
    rows = await session.scalars(
        select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
    )
    return [GradeCommentIn(grade=row.grade, comment_text=row.comment_text) for row in rows]


@router.put("/grade-comments")
async def save_grade_comments(
    payload: GradeCommentsIn, scope: CurrentScope, session: Db
) -> list[GradeCommentIn]:
    scope.require_director()
    existing = {
        row.grade: row
        for row in await session.scalars(
            select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
        )
    }
    for item in payload.comments:
        if item.grade in existing:
            existing[item.grade].comment_text = item.comment_text
        else:
            session.add(
                GradeComment(
                    campus_id=scope.campus_id,
                    grade=item.grade,
                    comment_text=item.comment_text,
                )
            )
    await session.commit()
    return await list_grade_comments(scope, session)


async def _context(
    session_id: int, student_id: int, scope, session: AsyncSession
) -> MessageContext:
    row = await _session_for_write(session, scope, session_id)
    klass = await session.get(Klass, row.class_id)

    enrolled = await _enrolled_students(session, klass.id, row.session_date)
    student = next((s for s in enrolled if s.id == student_id), None)
    if student is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")

    records = {
        record.student_id: record
        for record in await session.scalars(
            select(StudentDailyRecord).where(StudentDailyRecord.session_id == row.id)
        )
    }
    record = records.get(student_id)

    progress = await session.scalars(
        select(ClassSessionProgress)
        .where(ClassSessionProgress.session_id == row.id)
        .order_by(ClassSessionProgress.period)
    )
    campus = await session.get(Campus, scope.campus_id)
    teacher = await session.get(AppUser, klass.teacher_id) if klass.teacher_id else None
    comments = {
        item.grade: item.comment_text
        for item in await session.scalars(
            select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
        )
    }

    scores = [
        float(other.test_score_num)
        for other in records.values()
        if other.test_score_num is not None
    ]

    context = MessageContext(
        student_name=student.name,
        campus_name=campus.name,
        teacher_name=teacher.display_name if teacher else "담당",
        session_date=row.session_date,
        attendance=record.attendance_status if record else None,
        progress=[(item.period, item.content) for item in progress],
        homework_grade=record.homework_grade if record else None,
        grade_comment=comments.get(record.homework_grade) if record else None,
        test_name=row.test_name,
        test_score=_format_score(
            record.test_score_num if record else None,
            record.test_score_text if record else None,
        ),
        class_average=round(sum(scores) / len(scores), 1) if scores else None,
        homework=row.homework,
        video_url=row.video_url,
    )
    return context


@router.get("/preview")
async def preview(
    session_id: int, student_id: int, scope: CurrentScope, session: Db
) -> PreviewOut:
    context = await _context(session_id, student_id, scope, session)
    return PreviewOut(body=render_daily_message(context))


@router.get("/report-image")
async def report_image(
    session_id: int, student_id: int, scope: CurrentScope, session: Db
) -> Response:
    from .report import render_report_png  # 순환 임포트를 피해 호출 시점에 가져온다

    context = await _context(session_id, student_id, scope, session)
    return Response(render_report_png(context), media_type="image/png")
