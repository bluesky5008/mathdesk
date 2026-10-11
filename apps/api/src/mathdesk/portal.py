"""학생·학부모 포털 조회(FR-49 상세, AC-51, DES-26 상세, DCR-024·ADR-014).

`/api/portal` 아래의 모든 엔드포인트는 `current_portal_scope`만 쓴다. 응답 모델은 포털 전용으로
좁혀 다른 학생·보호자·연락처 정보를 담지 않는다. 계산은 기존 서비스의 내부 함수를 재사용한다.
"""
from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .daily import _is_recheck_target, has_records
from .db import get_session
from .messaging import _format_score
from .models import (
    AppUser,
    ClassSchedule,
    ClassSession,
    ClassSessionProgress,
    ConsultLog,
    Enrollment,
    Exam,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    GradeComment,
    Klass,
    MessageLog,
    Student,
    StudentDailyRecord,
)
from .scope import CurrentPortalScope, PortalScope
from .stats import StudentRound, student_rounds
from .timetable import _class_minutes

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/portal", tags=["portal"])

ATTENDING = ("present", "late", "early_leave")
SENT = ("sent", "fallback_sent")


# ── 응답 모델(포털 전용 — 다른 학생·연락처 정보 없음) ─────────────────


class PortalClass(BaseModel):
    id: int
    name: str
    teacher_name: str | None


class PortalStudent(BaseModel):
    id: int
    name: str
    grade: str | None
    status: str
    classes: list[PortalClass]


class Progress(BaseModel):
    period: int
    content: str | None


class Recheck(BaseModel):
    prev_grade: str
    prev_date: date
    result: str | None


class SessionRow(BaseModel):
    """문자 본문(FR-18 상세)과 같은 구획 구성 — 반 공통 다음에 본인 개별."""

    date: date
    class_name: str
    progress: list[Progress]
    homework: str | None
    video_url: str | None
    teacher_note: str | None
    test_name: str | None
    attendance: str
    attendance_reason: str | None
    homework_grade: str | None
    grade_comment: str | None
    recheck: Recheck | None
    test_score: str | None
    class_average: float | None
    comment: str | None


class AttendanceCount(BaseModel):
    present: int
    total: int


class TimetableRow(BaseModel):
    class_name: str
    weekday: int
    start_time: time
    end_time: time


class Summary(BaseModel):
    attendance: dict[str, AttendanceCount]
    latest_session: SessionRow | None
    latest_tests: list[StudentRound]
    timetable: list[TimetableRow]


class ExamRow(BaseModel):
    exam_id: int
    name: str
    exam_date: date | None
    score: float | None
    max_score: int | None


class Answer(BaseModel):
    no: int
    raw_value: str | None
    is_correct: bool | None
    points: int | None


class ExamDetail(ExamRow):
    answers: list[Answer]


class Consult(BaseModel):
    consulted_on: date
    content: str
    follow_up: str | None


class Message(BaseModel):
    sent_at: datetime
    body: str


# ── 학생 목록 ─────────────────────────────────────────────────────────


def _enrolled_on(on: date):
    return (
        (Enrollment.start_date <= on),
        or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on),
    )


async def _current_classes(session: AsyncSession, student_ids: tuple[int, ...]) -> dict[int, list[Klass]]:
    rows = await session.execute(
        select(Enrollment.student_id, Klass)
        .join(Klass, Klass.id == Enrollment.class_id)
        .where(Enrollment.student_id.in_(student_ids), *_enrolled_on(date.today()), Klass.is_active)
        .order_by(Klass.id)
    )
    classes: dict[int, list[Klass]] = {sid: [] for sid in student_ids}
    for student_id, klass in rows:
        classes[student_id].append(klass)
    return classes


async def _teacher_names(session: AsyncSession, classes: list[Klass]) -> dict[int, str]:
    ids = {k.teacher_id for k in classes if k.teacher_id}
    if not ids:
        return {}
    rows = await session.execute(select(AppUser.id, AppUser.display_name).where(AppUser.id.in_(ids)))
    return dict(rows.all())


@router.get("/students")
async def list_students(scope: CurrentPortalScope, session: Db) -> list[PortalStudent]:
    """연결된 학생(재원·휴원). 학부모 계정은 자녀 여럿일 수 있다."""
    students = list(
        await session.scalars(select(Student).where(Student.id.in_(scope.student_ids)).order_by(Student.id))
    )
    classes = await _current_classes(session, scope.student_ids)
    teachers = await _teacher_names(session, [k for ks in classes.values() for k in ks])
    return [
        PortalStudent(
            id=s.id, name=s.name, grade=s.grade, status=s.status,
            classes=[PortalClass(id=k.id, name=k.name, teacher_name=teachers.get(k.teacher_id)) for k in classes[s.id]],
        )
        for s in students
    ]


# ── 수업일별 기록 ───────────────────────────────────────────────────────


def _own(scope: PortalScope, student_id: int) -> int:
    scope.require_student(student_id)
    return student_id


async def _session_rows(
    session: AsyncSession, scope: PortalScope, student_id: int, before: date, limit: int
) -> list[SessionRow]:
    """학생이 배정되어 있던, 기록이 있는 수업만 최신 순(어느 반이든). `daily._history`와 같은 규칙."""
    rows = (
        await session.execute(
            select(ClassSession, Klass)
            .join(Klass, Klass.id == ClassSession.class_id)
            .join(
                Enrollment,
                (Enrollment.class_id == ClassSession.class_id)
                & (Enrollment.student_id == student_id)
                & (Enrollment.start_date <= ClassSession.session_date)
                & or_(Enrollment.end_date.is_(None), Enrollment.end_date >= ClassSession.session_date),
            )
            .where(has_records(), ClassSession.session_date <= before)
            .order_by(ClassSession.session_date.desc(), ClassSession.id.desc())
            .limit(limit)
        )
    ).all()
    if not rows:
        return []
    session_ids = [s.id for s, _ in rows]
    scores: dict[int, list[float]] = {}
    mine: dict[int, StudentDailyRecord] = {}
    for record in await session.scalars(
        select(StudentDailyRecord).where(StudentDailyRecord.session_id.in_(session_ids))
    ):
        if record.test_score_num is not None:
            scores.setdefault(record.session_id, []).append(float(record.test_score_num))
        if record.student_id == student_id:
            mine[record.session_id] = record
    progress: dict[int, list[Progress]] = {}
    for item in await session.scalars(
        select(ClassSessionProgress)
        .where(ClassSessionProgress.session_id.in_(session_ids))
        .order_by(ClassSessionProgress.period)
    ):
        progress.setdefault(item.session_id, []).append(Progress(period=item.period, content=item.content))
    comments = dict(
        (await session.execute(
            select(GradeComment.grade, GradeComment.comment_text).where(GradeComment.campus_id == scope.campus_id)
        )).all()
    )
    # 재검사 판정: 같은 반의 직전 등급(DES-05 상세)
    graded = (
        await session.execute(
            select(ClassSession.class_id, ClassSession.session_date, StudentDailyRecord.homework_grade)
            .join(ClassSession, ClassSession.id == StudentDailyRecord.session_id)
            .where(StudentDailyRecord.student_id == student_id, StudentDailyRecord.homework_grade.is_not(None))
            .order_by(ClassSession.session_date.desc())
        )
    ).all()

    out = []
    for row, klass in rows:
        record = mine.get(row.id)
        prev = next(((g, on) for cid, on, g in graded if cid == row.class_id and on < row.session_date), None)
        recheck = (
            Recheck(prev_grade=prev[0], prev_date=prev[1], result=record.recheck_result if record else None)
            if prev and _is_recheck_target(prev[0])
            else None
        )
        averages = scores.get(row.id)
        out.append(SessionRow(
            date=row.session_date,
            class_name=klass.name,
            progress=progress.get(row.id, []),
            homework=row.homework,
            video_url=row.video_url,
            teacher_note=row.teacher_note,
            test_name=row.test_name,
            attendance=record.attendance_status if record else "unchecked",
            attendance_reason=record.attendance_reason if record else None,
            homework_grade=record.homework_grade if record else None,
            grade_comment=comments.get(record.homework_grade) if record and record.homework_grade else None,
            recheck=recheck,
            test_score=_format_score(record.test_score_num, record.test_score_text) if record else None,
            class_average=round(sum(averages) / len(averages), 1) if averages else None,
            comment=record.comment if record else None,
        ))
    return out


@router.get("/students/{student_id}/sessions")
async def read_sessions(
    student_id: int,
    scope: CurrentPortalScope,
    session: Db,
    before: date | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[SessionRow]:
    return await _session_rows(session, scope, _own(scope, student_id), before or date.today(), limit)


# ── 홈 요약 ─────────────────────────────────────────────────────────────


async def _attendance(session: AsyncSession, student_id: int, since: date | None) -> AttendanceCount:
    statement = (
        select(StudentDailyRecord.attendance_status)
        .join(ClassSession, ClassSession.id == StudentDailyRecord.session_id)
        .where(StudentDailyRecord.student_id == student_id, StudentDailyRecord.attendance_status != "unchecked")
    )
    if since is not None:
        statement = statement.where(ClassSession.session_date >= since)
    statuses = list(await session.scalars(statement))
    return AttendanceCount(present=sum(s in ATTENDING for s in statuses), total=len(statuses))


async def _rounds(session: AsyncSession, student_id: int, anchor: date) -> list[StudentRound]:
    klass = await session.scalar(
        select(Klass)
        .join(Enrollment, Enrollment.class_id == Klass.id)
        .where(Enrollment.student_id == student_id, *_enrolled_on(anchor))
        .order_by(Klass.id)
        .limit(1)
    )
    return await student_rounds(session, student_id, klass, anchor)


@router.get("/students/{student_id}/summary")
async def read_summary(student_id: int, scope: CurrentPortalScope, session: Db) -> Summary:
    _own(scope, student_id)
    today = date.today()
    classes = (await _current_classes(session, (student_id,)))[student_id]
    length = timedelta(minutes=await _class_minutes(session, scope.campus_id))
    schedules = await session.scalars(
        select(ClassSchedule).where(ClassSchedule.class_id.in_([k.id for k in classes]))
    )
    names = {k.id: k.name for k in classes}
    timetable = [
        TimetableRow(
            class_name=names[s.class_id], weekday=s.weekday, start_time=s.start_time,
            end_time=(datetime.combine(datetime.min, s.start_time) + length).time(),
        )
        for s in schedules
    ]
    timetable.sort(key=lambda r: (r.weekday, r.start_time, r.class_name))
    latest = await _session_rows(session, scope, student_id, today, 1)
    return Summary(
        attendance={
            "last_30_days": await _attendance(session, student_id, today - timedelta(days=30)),
            "all_time": await _attendance(session, student_id, None),
        },
        latest_session=latest[0] if latest else None,
        latest_tests=(await _rounds(session, student_id, today))[-3:],
        timetable=timetable,
    )


@router.get("/students/{student_id}/test-trend")
async def read_test_trend(
    student_id: int,
    scope: CurrentPortalScope,
    session: Db,
    count: Annotated[int, Query(ge=1, le=20)] = 10,
) -> dict:
    rounds = await _rounds(session, _own(scope, student_id), date.today())
    return {"total": len(rounds), "rounds": rounds[-count:]}


# ── 시험 결과 ───────────────────────────────────────────────────────────


def _exam_row(exam: Exam, attempt: ExamAttempt) -> dict:
    return {
        "exam_id": exam.id, "name": exam.name, "exam_date": exam.exam_date,
        "score": None if attempt.score is None else float(attempt.score), "max_score": exam.max_score,
    }


@router.get("/students/{student_id}/exams")
async def read_exams(student_id: int, scope: CurrentPortalScope, session: Db) -> list[ExamRow]:
    rows = await session.execute(
        select(Exam, ExamAttempt)
        .join(ExamAttempt, ExamAttempt.exam_id == Exam.id)
        .where(ExamAttempt.student_id == _own(scope, student_id), ExamAttempt.score.is_not(None))
        .order_by(Exam.exam_date.desc().nulls_last(), Exam.id.desc())
    )
    return [ExamRow(**_exam_row(exam, attempt)) for exam, attempt in rows]


@router.get("/students/{student_id}/exams/{exam_id}")
async def read_exam(student_id: int, exam_id: int, scope: CurrentPortalScope, session: Db) -> ExamDetail:
    row = (
        await session.execute(
            select(Exam, ExamAttempt)
            .join(ExamAttempt, ExamAttempt.exam_id == Exam.id)
            .where(ExamAttempt.student_id == _own(scope, student_id), Exam.id == exam_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")
    exam, attempt = row
    points = dict((await session.execute(
        select(ExamQuestion.no, ExamQuestion.points).where(ExamQuestion.exam_id == exam.id)
    )).all())
    answers = await session.scalars(
        select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id).order_by(ExamAnswer.question_no)
    )
    return ExamDetail(
        **_exam_row(exam, attempt),
        answers=[
            Answer(no=a.question_no, raw_value=a.raw_value, is_correct=a.is_correct, points=points.get(a.question_no))
            for a in answers
        ],
    )


# ── 상담·받은 문자 ─────────────────────────────────────────────────────


@router.get("/students/{student_id}/consults")
async def read_consults(student_id: int, scope: CurrentPortalScope, session: Db) -> list[Consult]:
    """본인 상담 기록 전부(방식 A, DCR-024)."""
    rows = await session.scalars(
        select(ConsultLog)
        .where(ConsultLog.student_id == _own(scope, student_id))
        .order_by(ConsultLog.consulted_on.desc(), ConsultLog.id.desc())
    )
    return [Consult(consulted_on=c.consulted_on, content=c.content, follow_up=c.follow_up) for c in rows]


@router.get("/students/{student_id}/messages")
async def read_messages(
    student_id: int,
    scope: CurrentPortalScope,
    session: Db,
    before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[Message]:
    """성공 발송의 본문. 같은 세션에 학생·학부모 두 번 보냈으면 본문이 같으므로 한 건으로 보인다."""
    statement = (
        select(MessageLog)
        .where(
            MessageLog.student_id == _own(scope, student_id),
            MessageLog.status.in_(SENT),
            MessageLog.is_test.is_(False),
        )
        .order_by(MessageLog.requested_at.desc(), MessageLog.id.desc())
    )
    if before is not None:
        statement = statement.where(MessageLog.requested_at < before)
    out: list[Message] = []
    seen: set = set()
    for log in await session.scalars(statement):
        key = log.session_id if log.session_id is not None else ("body", log.body_snapshot)
        if key in seen:
            continue
        seen.add(key)
        out.append(Message(sent_at=log.requested_at, body=log.body_snapshot))
        if len(out) == limit:
            break
    return out
