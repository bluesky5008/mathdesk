import os
from datetime import date, timedelta
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from openpyxl import Workbook
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
from .scope import CurrentScope, Scope, ScopedRepository

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


# ── 통계 (FR-24~FR-26) ────────────────────────────────────────────────
# DES-06대로 저장 집계 테이블 없이 SQL 집계로 계산한다.


class StudentWeek(BaseModel):
    week_start: date
    test_average: float | None
    class_test_average: float | None
    homework_grades: list[str]
    homework_completion: float | None
    class_homework_completion: float | None
    attendance_rate: float | None


class StudentHistoryOut(BaseModel):
    student: dict[str, str | int]
    klass: dict[str, str | int] | None
    weeks: list[StudentWeek]


class StudentRow(BaseModel):
    student_id: int
    name: str
    test_average: float | None
    homework_completion: float | None
    attendance_rate: float | None


class Bucket(BaseModel):
    bucket: str
    count: int


class PeriodStats(BaseModel):
    start: date
    end: date
    students: list[StudentRow]
    test: dict[str, float | int | None | list[Bucket]]
    homework: dict[str, float | None | dict[str, int]]
    attendance_rate: float | None


class ClassStatsOut(BaseModel):
    klass: dict[str, str | int]
    period: PeriodStats
    compare: PeriodStats | None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _rate(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _bucket(score: float) -> str:
    """10점 구간. 만점 100을 90~100 한 칸으로 묶어 마지막 칸이 1점짜리가 되지 않게 한다."""
    floor = min(int(score // 10) * 10, 90)
    return f"{floor}~{100 if floor == 90 else floor + 9}"


async def _period_records(
    session: AsyncSession, class_id: int, start: date, end: date
) -> list[tuple[StudentDailyRecord, date]]:
    rows = await session.execute(
        select(StudentDailyRecord, ClassSession.session_date)
        .join(ClassSession, ClassSession.id == StudentDailyRecord.session_id)
        .where(
            ClassSession.class_id == class_id,
            ClassSession.session_date.between(start, end),
        )
        .order_by(ClassSession.session_date)
    )
    return [(record, session_date) for record, session_date in rows]


async def _session_count(
    session: AsyncSession, class_id: int, start: date, end: date
) -> int:
    return (
        await session.scalar(
            select(func.count(ClassSession.id)).where(
                ClassSession.class_id == class_id,
                ClassSession.session_date.between(start, end),
            )
        )
        or 0
    )


async def _current_class(
    session: AsyncSession, scope: Scope, student_id: int, on: date
) -> Klass | None:
    """강사는 담당 반만 본다(설계의 권한 표). 담당 반이 아니면 반이 없는 것으로 본다."""
    statement = (
        select(Klass)
        .join(Enrollment, Enrollment.class_id == Klass.id)
        .where(
            Klass.campus_id == scope.campus_id,
            Enrollment.student_id == student_id,
            Enrollment.start_date <= on,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on),
        )
    )
    if not scope.is_director:
        statement = statement.where(Klass.teacher_id == scope.user.id)
    return await session.scalar(statement.order_by(Klass.id).limit(1))


@router.get("/stats/students/{student_id}")
async def student_history(
    student_id: int,
    scope: CurrentScope,
    session: Db,
    to: date | None = None,
    weeks: int = 8,
    class_id: int | None = None,
) -> StudentHistoryOut:
    """주 단위 시계열과 같은 주의 반 평균을 함께 준다(FR-24, AC-19)."""
    student = await ScopedRepository(session, scope).get(Student, student_id)
    anchor = to or date.today()
    klass = (
        await _visible_class(session, scope, class_id)
        if class_id is not None
        else await _current_class(session, scope, student_id, anchor)
    )
    if klass is None and not scope.is_director:
        # 담당 반의 학생이 아니면 이름조차 돌려주지 않는다.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")

    last_monday, _ = _week_bounds(anchor)
    timeline: list[StudentWeek] = []
    for index in range(weeks - 1, -1, -1):
        start = last_monday - timedelta(days=7 * index)
        end = start + timedelta(days=6)
        if klass is None:
            timeline.append(
                StudentWeek(
                    week_start=start,
                    test_average=None,
                    class_test_average=None,
                    homework_grades=[],
                    homework_completion=None,
                    class_homework_completion=None,
                    attendance_rate=None,
                )
            )
            continue

        records = await _period_records(session, klass.id, start, end)
        mine = [record for record, _ in records if record.student_id == student_id]
        sessions = await _session_count(session, klass.id, start, end)
        grades = [record.homework_grade for record in mine if record.homework_grade]
        timeline.append(
            StudentWeek(
                week_start=start,
                test_average=_mean(
                    [float(r.test_score_num) for r in mine if r.test_score_num is not None]
                ),
                class_test_average=_mean(
                    [
                        float(record.test_score_num)
                        for record, _ in records
                        if record.test_score_num is not None
                    ]
                ),
                homework_grades=grades,
                homework_completion=_completion_rate(grades),
                class_homework_completion=_completion_rate(
                    [record.homework_grade for record, _ in records if record.homework_grade]
                ),
                attendance_rate=_rate(
                    sum(1 for record in mine if record.attendance_status in ATTENDING),
                    sessions,
                ),
            )
        )

    return StudentHistoryOut(
        student={"id": student.id, "name": student.name},
        klass={"id": klass.id, "name": klass.name} if klass else None,
        weeks=timeline,
    )


async def _period_stats(
    session: AsyncSession, klass: Klass, start: date, end: date
) -> PeriodStats:
    records = await _period_records(session, klass.id, start, end)
    sessions = await _session_count(session, klass.id, start, end)
    roster = list(
        await session.scalars(
            select(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .where(
                Enrollment.class_id == klass.id,
                Enrollment.start_date <= end,
                or_(Enrollment.end_date.is_(None), Enrollment.end_date >= start),
            )
            .order_by(Student.id)
        )
    )

    rows = []
    for student in roster:
        mine = [record for record, _ in records if record.student_id == student.id]
        grades = [record.homework_grade for record in mine if record.homework_grade]
        rows.append(
            StudentRow(
                student_id=student.id,
                name=student.name,
                test_average=_mean(
                    [float(r.test_score_num) for r in mine if r.test_score_num is not None]
                ),
                homework_completion=_completion_rate(grades),
                attendance_rate=_rate(
                    sum(1 for record in mine if record.attendance_status in ATTENDING),
                    sessions,
                ),
            )
        )

    scores = [float(r.test_score_num) for r, _ in records if r.test_score_num is not None]
    distribution: dict[str, int] = {}
    for score in scores:
        distribution[_bucket(score)] = distribution.get(_bucket(score), 0) + 1
    grades = [record.homework_grade for record, _ in records if record.homework_grade]
    grade_counts: dict[str, int] = {}
    for grade in sorted(grades, key=HOMEWORK_GRADE.index):
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    return PeriodStats(
        start=start,
        end=end,
        students=rows,
        test={
            "average": _mean(scores),
            "count": len(scores),
            "distribution": [
                Bucket(bucket=bucket, count=count)
                for bucket, count in sorted(distribution.items())
            ],
        },
        homework={
            "completion_rate": _completion_rate(grades),
            "distribution": grade_counts,
        },
        attendance_rate=_rate(
            sum(1 for record, _ in records if record.attendance_status in ATTENDING),
            sessions * len(roster),
        ),
    )


@router.get("/stats/classes/{class_id}")
async def class_stats(
    class_id: int,
    start: date,
    end: date,
    scope: CurrentScope,
    session: Db,
    compare_start: date | None = None,
    compare_end: date | None = None,
) -> ClassStatsOut:
    """기간 통계와 선택한 비교 기간을 함께 준다(FR-25)."""
    klass = await _visible_class(session, scope, class_id)
    compare = None
    if compare_start is not None and compare_end is not None:
        compare = await _period_stats(session, klass, compare_start, compare_end)
    return ClassStatsOut(
        klass={"id": klass.id, "name": klass.name},
        period=await _period_stats(session, klass, start, end),
        compare=compare,
    )


EXPORT_HEADER = ["학생", "테스트 평균", "과제 완수율", "출결률"]
EXPORT_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.get("/stats/export")
async def export_class_stats(
    class_id: int, start: date, end: date, scope: CurrentScope, session: Db
) -> Response:
    """통계 화면의 학생 행을 그대로 엑셀로 내보낸다(FR-26, AC-20)."""
    klass = await _visible_class(session, scope, class_id)
    stats = await _period_stats(session, klass, start, end)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "통계"
    sheet.append(EXPORT_HEADER)
    for row in stats.students:
        sheet.append([row.name, row.test_average, row.homework_completion, row.attendance_rate])

    buffer = BytesIO()
    workbook.save(buffer)
    filename = f"mathdesk-stats-{klass.id}-{start}-{end}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type=EXPORT_MEDIA_TYPE,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )
