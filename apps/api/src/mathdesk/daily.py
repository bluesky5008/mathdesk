import os
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import (
    AuditLog,
    ClassSession,
    ClassSessionProgress,
    Enrollment,
    Klass,
    Student,
    StudentDailyRecord,
)
from .models.daily import ATTENDANCE_STATUS, HOMEWORK_GRADE
from .scope import CurrentScope, Scope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/daily", tags=["daily"])

ATTENDING = ("present", "late", "early_leave")
STATUS_PATTERN = "^(%s)$" % "|".join(ATTENDANCE_STATUS)
# 재검사 대상 판정 기준 등급(FR-12). 이 등급 이하면 다음 수업에서 재검사 대상이다.
RECHECK_THRESHOLD_GRADE = os.environ.get("MATHDESK_RECHECK_THRESHOLD_GRADE", "B")
GRADE_PATTERN = "^(%s)$" % "|".join(re.escape(grade) for grade in HOMEWORK_GRADE)


class ProgressItem(BaseModel):
    period: int = Field(ge=1, le=4)
    content: str | None = None


class NotesIn(BaseModel):
    """반 단위 메모 저장. 보내지 않은 필드는 건드리지 않는다."""

    progress: list[ProgressItem] | None = None
    homework: str | None = None
    video_url: str | None = None
    teacher_note: str | None = None
    test_name: str | None = None
    test_max_score: int | None = None


class RecordIn(BaseModel):
    """표 일괄 저장. 보내지 않은 필드는 건드리지 않는다."""

    student_id: int
    attendance_status: str | None = Field(default=None, pattern=STATUS_PATTERN)
    attendance_reason: str | None = None
    homework_grade: str | None = Field(default=None, pattern=GRADE_PATTERN)
    test_score_num: Decimal | None = None
    test_score_text: str | None = None


class RecordsIn(BaseModel):
    records: list[RecordIn]


class RecheckIn(BaseModel):
    result: str | None = Field(default=None, pattern="^(pass|fail)$")


class SessionOut(BaseModel):
    id: int
    class_id: int
    session_date: date
    progress: list[ProgressItem]
    homework: str | None
    video_url: str | None
    teacher_note: str | None
    test_name: str | None
    test_max_score: int | None
    attendance_confirmed_at: str | None


class RecheckOut(BaseModel):
    target: bool
    prev_grade: str | None
    prev_date: date | None
    result: str | None


class RecordOut(BaseModel):
    student_id: int
    name: str
    attendance_status: str
    attendance_reason: str | None
    homework_grade: str | None
    recheck: RecheckOut
    test_score_num: Decimal | None
    test_score_text: str | None


class SummaryOut(BaseModel):
    enrolled: int
    attending: int
    test_average: float | None
    test_count: int


class DailyOut(BaseModel):
    session: SessionOut
    records: list[RecordOut]
    summary: SummaryOut


def _forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")


async def _visible_class(session: AsyncSession, scope: Scope, class_id: int) -> Klass:
    statement = select(Klass).where(
        Klass.id == class_id, Klass.campus_id == scope.campus_id
    )
    if not scope.is_director:
        statement = statement.where(Klass.teacher_id == scope.user.id)
    klass = await session.scalar(statement)
    if klass is None:
        raise _forbidden()
    return klass


async def _get_or_create_session(
    session: AsyncSession, class_id: int, on: date
) -> ClassSession:
    """설계 REST 계약에 세션 생성 엔드포인트가 없으므로 조회 시점에 만든다(DES-05)."""
    existing = await session.scalar(
        select(ClassSession).where(
            ClassSession.class_id == class_id, ClassSession.session_date == on
        )
    )
    if existing is not None:
        return existing
    created = ClassSession(class_id=class_id, session_date=on)
    session.add(created)
    await session.commit()
    await session.refresh(created)
    return created


async def _session_for_write(
    session: AsyncSession, scope: Scope, session_id: int
) -> ClassSession:
    row = await session.get(ClassSession, session_id)
    if row is None:
        raise _forbidden()
    await _visible_class(session, scope, row.class_id)
    return row


def _is_recheck_target(grade: str | None) -> bool:
    if grade is None or RECHECK_THRESHOLD_GRADE not in HOMEWORK_GRADE:
        return False
    return HOMEWORK_GRADE.index(grade) >= HOMEWORK_GRADE.index(RECHECK_THRESHOLD_GRADE)


async def _previous_grades(
    session: AsyncSession, class_id: int, on: date, student_ids: list[int]
) -> dict[int, tuple[str, date]]:
    """직전 수업의 과제 등급. 저장하지 않고 조회할 때마다 계산한다(기준 등급이 설정값이므로)."""
    if not student_ids:
        return {}
    rows = await session.execute(
        select(
            StudentDailyRecord.student_id,
            StudentDailyRecord.homework_grade,
            ClassSession.session_date,
        )
        .join(ClassSession, ClassSession.id == StudentDailyRecord.session_id)
        .where(
            ClassSession.class_id == class_id,
            ClassSession.session_date < on,
            StudentDailyRecord.student_id.in_(student_ids),
            StudentDailyRecord.homework_grade.is_not(None),
        )
        .order_by(ClassSession.session_date.desc())
    )
    latest: dict[int, tuple[str, date]] = {}
    for student_id, grade, session_date in rows:
        latest.setdefault(student_id, (grade, session_date))
    return latest


async def _enrolled_students(
    session: AsyncSession, class_id: int, on: date
) -> list[Student]:
    return list(
        await session.scalars(
            select(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .where(
                Enrollment.class_id == class_id,
                Enrollment.start_date <= on,
                or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on),
            )
            .order_by(Student.id)
        )
    )


async def _build_response(
    session: AsyncSession, klass: Klass, row: ClassSession
) -> DailyOut:
    students = await _enrolled_students(session, klass.id, row.session_date)
    stored = {
        record.student_id: record
        for record in await session.scalars(
            select(StudentDailyRecord).where(StudentDailyRecord.session_id == row.id)
        )
    }
    progress = await session.scalars(
        select(ClassSessionProgress)
        .where(ClassSessionProgress.session_id == row.id)
        .order_by(ClassSessionProgress.period)
    )

    previous = await _previous_grades(
        session, klass.id, row.session_date, [student.id for student in students]
    )

    records = []
    for student in students:
        record = stored.get(student.id)
        prev_grade, prev_date = previous.get(student.id, (None, None))
        records.append(
            RecordOut(
                student_id=student.id,
                name=student.name,
                attendance_status=record.attendance_status if record else "unchecked",
                attendance_reason=record.attendance_reason if record else None,
                homework_grade=record.homework_grade if record else None,
                recheck=RecheckOut(
                    target=_is_recheck_target(prev_grade),
                    prev_grade=prev_grade,
                    prev_date=prev_date,
                    result=record.recheck_result if record else None,
                ),
                test_score_num=record.test_score_num if record else None,
                test_score_text=record.test_score_text if record else None,
            )
        )

    scores = [record.test_score_num for record in records if record.test_score_num is not None]
    return DailyOut(
        session=SessionOut(
            id=row.id,
            class_id=row.class_id,
            session_date=row.session_date,
            progress=[
                ProgressItem(period=item.period, content=item.content) for item in progress
            ],
            homework=row.homework,
            video_url=row.video_url,
            teacher_note=row.teacher_note,
            test_name=row.test_name,
            test_max_score=row.test_max_score,
            attendance_confirmed_at=(
                row.attendance_confirmed_at.isoformat()
                if row.attendance_confirmed_at
                else None
            ),
        ),
        records=records,
        summary=SummaryOut(
            enrolled=len(records),
            attending=sum(1 for r in records if r.attendance_status in ATTENDING),
            test_average=(
                round(float(sum(scores)) / len(scores), 1) if scores else None
            ),
            test_count=len(scores),
        ),
    )


async def _record_for(
    session: AsyncSession, session_id: int, student_id: int
) -> StudentDailyRecord:
    record = await session.scalar(
        select(StudentDailyRecord).where(
            StudentDailyRecord.session_id == session_id,
            StudentDailyRecord.student_id == student_id,
        )
    )
    if record is None:
        record = StudentDailyRecord(session_id=session_id, student_id=student_id)
        session.add(record)
    return record


@router.get("")
async def read_daily(
    class_id: int, date: date, scope: CurrentScope, session: Db
) -> DailyOut:
    klass = await _visible_class(session, scope, class_id)
    row = await _get_or_create_session(session, class_id, date)
    return await _build_response(session, klass, row)


@router.put("/{session_id}/notes")
async def save_notes(
    session_id: int, payload: NotesIn, scope: CurrentScope, session: Db
) -> DailyOut:
    row = await _session_for_write(session, scope, session_id)
    fields = payload.model_dump(exclude_unset=True)

    if "progress" in fields:
        for existing in await session.scalars(
            select(ClassSessionProgress).where(ClassSessionProgress.session_id == row.id)
        ):
            await session.delete(existing)
        for item in payload.progress or []:
            session.add(
                ClassSessionProgress(
                    session_id=row.id, period=item.period, content=item.content
                )
            )
    for field, value in fields.items():
        if field != "progress":
            setattr(row, field, value)

    await session.commit()
    klass = await session.get(Klass, row.class_id)
    return await _build_response(session, klass, row)


@router.put("/{session_id}/records")
async def save_records(
    session_id: int, payload: RecordsIn, scope: CurrentScope, session: Db
) -> DailyOut:
    row = await _session_for_write(session, scope, session_id)
    enrolled = {
        student.id for student in await _enrolled_students(session, row.class_id, row.session_date)
    }

    for item in payload.records:
        if item.student_id not in enrolled:
            raise _forbidden()
        fields = item.model_dump(exclude_unset=True, exclude={"student_id"})
        if row.attendance_confirmed_at is not None and (
            {"attendance_status", "attendance_reason"} & fields.keys()
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "출결이 확정되었습니다. 편집을 눌러 해제한 뒤 수정하세요.",
            )
        record = await _record_for(session, row.id, item.student_id)
        for field, value in fields.items():
            setattr(record, field, value)

    await session.commit()
    klass = await session.get(Klass, row.class_id)
    return await _build_response(session, klass, row)


@router.put("/{session_id}/records/{student_id}/recheck")
async def save_recheck(
    session_id: int, student_id: int, payload: RecheckIn, scope: CurrentScope, session: Db
) -> DailyOut:
    row = await _session_for_write(session, scope, session_id)
    record = await _record_for(session, row.id, student_id)
    record.recheck_result = payload.result
    await session.commit()
    klass = await session.get(Klass, row.class_id)
    return await _build_response(session, klass, row)


async def _set_confirmation(
    session: AsyncSession, scope: Scope, session_id: int, confirmed: bool
) -> DailyOut:
    row = await _session_for_write(session, scope, session_id)
    klass = await session.get(Klass, row.class_id)

    row.attendance_confirmed_at = datetime.now(UTC) if confirmed else None
    row.attendance_confirmed_by = scope.user.id if confirmed else None
    session.add(
        AuditLog(
            campus_id=scope.campus_id,
            actor_id=scope.user.id,
            action="attendance.confirm" if confirmed else "attendance.unlock",
            target=f"class_session:{row.id}",
            detail=f"{klass.name} {row.session_date}",
        )
    )
    await session.commit()
    return await _build_response(session, klass, row)


@router.post("/{session_id}/attendance/confirm")
async def confirm_attendance(
    session_id: int, scope: CurrentScope, session: Db
) -> DailyOut:
    return await _set_confirmation(session, scope, session_id, confirmed=True)


@router.post("/{session_id}/attendance/unlock")
async def unlock_attendance(
    session_id: int, scope: CurrentScope, session: Db
) -> DailyOut:
    return await _set_confirmation(session, scope, session_id, confirmed=False)
