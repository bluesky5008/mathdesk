import os
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .daily import ProgressItem, _previous_grades, _visible_class, _is_recheck_target
from .db import get_session
from .models import (
    ClassSession,
    ClassSessionProgress,
    Enrollment,
    Klass,
    Student,
    StudentDailyRecord,
)
from .models.daily import HOMEWORK_GRADE
from .scope import CurrentScope, Scope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["dashboard"])

ATTENDING = ("present", "late", "early_leave")
MISSING_GRADE = "F"  # 미제출로 취급하는 등급


def _pass_grade() -> str:
    """과제 완수로 인정하는 최저 등급(FR-15). 설정값이며 기본은 B다."""
    return os.environ.get("MATHDESK_HOMEWORK_PASS_GRADE", "B")


def _week_bounds(on: date) -> tuple[date, date]:
    monday = on - timedelta(days=on.weekday())
    return monday, monday + timedelta(days=6)


class CampusSummary(BaseModel):
    enrolled_students: int
    active_classes: int


class AttendanceSummary(BaseModel):
    class_id: int
    class_name: str
    enrolled: int
    attending: int


class HomeworkSummary(BaseModel):
    completion_rate: float | None
    delta_points: float | None
    missing: int
    recheck_targets: int


class TestSummary(BaseModel):
    average: float | None
    count: int
    max: float | None
    max_count: int
    min: float | None


class LastSessionSummary(BaseModel):
    session_date: date
    progress: list[ProgressItem]
    homework: str | None


class DashboardOut(BaseModel):
    campus: CampusSummary
    attendance: AttendanceSummary | None
    homework: HomeworkSummary
    test: TestSummary
    last_session: LastSessionSummary | None


def _week_records(scope: Scope, class_id: int, start: date, end: date) -> Select:
    return (
        select(StudentDailyRecord, ClassSession.session_date)
        .join(ClassSession, ClassSession.id == StudentDailyRecord.session_id)
        .join(Klass, Klass.id == ClassSession.class_id)
        .where(
            Klass.campus_id == scope.campus_id,
            ClassSession.class_id == class_id,
            ClassSession.session_date.between(start, end),
        )
    )


async def _grades_in(session: AsyncSession, statement: Select) -> list[str]:
    rows = await session.execute(statement)
    return [record.homework_grade for record, _ in rows if record.homework_grade]


def _completion_rate(grades: list[str]) -> float | None:
    if not grades:
        return None
    threshold = HOMEWORK_GRADE.index(_pass_grade())
    passed = sum(1 for grade in grades if HOMEWORK_GRADE.index(grade) <= threshold)
    return round(passed * 100 / len(grades), 1)


@router.get("/dashboard")
async def dashboard(
    class_id: int, date: date, scope: CurrentScope, session: Db
) -> DashboardOut:
    klass = await _visible_class(session, scope, class_id)
    start, end = _week_bounds(date)

    enrolled_students = await session.scalar(
        select(func.count(Student.id)).where(
            Student.campus_id == scope.campus_id, Student.status == "enrolled"
        )
    )
    active_classes = await session.scalar(
        select(func.count(Klass.id)).where(
            Klass.campus_id == scope.campus_id, Klass.is_active
        )
    )

    roster = list(
        await session.scalars(
            select(Enrollment.student_id).where(
                Enrollment.class_id == class_id,
                Enrollment.start_date <= date,
                or_(Enrollment.end_date.is_(None), Enrollment.end_date >= date),
            )
        )
    )
    today_session = await session.scalar(
        select(ClassSession).where(
            ClassSession.class_id == class_id, ClassSession.session_date == date
        )
    )
    attending = 0
    if today_session is not None:
        attending = await session.scalar(
            select(func.count(StudentDailyRecord.id)).where(
                StudentDailyRecord.session_id == today_session.id,
                StudentDailyRecord.attendance_status.in_(ATTENDING),
            )
        )

    this_week = await _grades_in(session, _week_records(scope, class_id, start, end))
    previous_start = start - timedelta(days=7)
    last_week = await _grades_in(
        session, _week_records(scope, class_id, previous_start, start - timedelta(days=1))
    )
    this_rate, last_rate = _completion_rate(this_week), _completion_rate(last_week)

    missing = sum(1 for grade in this_week if grade == MISSING_GRADE)

    week_sessions = list(
        await session.scalars(
            select(ClassSession)
            .where(
                ClassSession.class_id == class_id,
                ClassSession.session_date.between(start, end),
            )
            .order_by(ClassSession.session_date)
        )
    )
    recheck_targets: set[int] = set()
    for week_session in week_sessions:
        previous = await _previous_grades(
            session, class_id, week_session.session_date, roster
        )
        recheck_targets |= {
            student_id
            for student_id, (grade, _) in previous.items()
            if _is_recheck_target(grade)
        }

    scores = [
        float(record.test_score_num)
        for record, _ in await session.execute(_week_records(scope, class_id, start, end))
        if record.test_score_num is not None
    ]
    highest = max(scores) if scores else None

    previous_session = await session.scalar(
        select(ClassSession)
        .where(ClassSession.class_id == class_id, ClassSession.session_date < date)
        .order_by(ClassSession.session_date.desc())
        .limit(1)
    )
    last_session = None
    if previous_session is not None:
        progress = await session.scalars(
            select(ClassSessionProgress)
            .where(ClassSessionProgress.session_id == previous_session.id)
            .order_by(ClassSessionProgress.period)
        )
        last_session = LastSessionSummary(
            session_date=previous_session.session_date,
            progress=[ProgressItem(period=p.period, content=p.content) for p in progress],
            homework=previous_session.homework,
        )

    return DashboardOut(
        campus=CampusSummary(
            enrolled_students=enrolled_students or 0, active_classes=active_classes or 0
        ),
        attendance=AttendanceSummary(
            class_id=class_id,
            class_name=klass.name,
            enrolled=len(roster),
            attending=attending or 0,
        ),
        homework=HomeworkSummary(
            completion_rate=this_rate,
            delta_points=(
                round(this_rate - last_rate, 1)
                if this_rate is not None and last_rate is not None
                else None
            ),
            missing=missing,
            recheck_targets=len(recheck_targets),
        ),
        test=TestSummary(
            average=round(sum(scores) / len(scores), 1) if scores else None,
            count=len(scores),
            max=highest,
            max_count=sum(1 for score in scores if score == highest) if scores else 0,
            min=min(scores) if scores else None,
        ),
        last_session=last_session,
    )
